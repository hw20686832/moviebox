#!/usr/bin/env python
# coding:utf-8
#from __future__ import unicode_literals

import os
import sys
import re
import json
import random
import zipfile
import StringIO
import datetime

import celery
from celery.bin import worker
from celery.utils.log import get_task_logger
from kombu import Queue

import requests
import youtube_dl
from lxml import html
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

import settings


LIST_URL = "http://sbfunapi.cc/data/data_en.zip?q=%s"
TRAILERS_LIST_URL = "http://sbfunapi.cc/api/serials/trailers_movies/?feed=popular"
TRAILER_DETAIL_URL = "http://sbfunapi.cc/api/serials/trailers/?id=%s"
MOVIE_DETAIL_URL = "http://sbfunapi.cc/api/serials/movie_details/?id=%s"
TV_DETAIL_URL = "http://sbfunapi.cc/api/serials/es/?season=%s&id=%s"

IMDB_PAGE_URL = "http://www.imdb.com/title/%s/"
IMDB_TRAILER_URL = "http://www.imdb.com/title/%s/videogallery"


class Config(object):
    BROKER_URL = "redis://:%(password)s@%(host)s:%(port)d/%(db)d" % settings.REDIS_CONF
    CELERY_TASK_RESULT_EXPIRES = 3600
    CELERY_ACCEPT_CONTENT = ['json', ]
    CELERY_TASK_SERIALIZER = 'json'

    CELERY_QUEUES = (
        Queue('info', routing_key='moviebox.parse_#'),
        Queue('video', routing_key='moviebox.download_#')
    )

    CELERY_DEFAULT_QUEUE = 'info'
    CELERY_DEFAULT_EXCHANGE_TYPE = 'topic'
    CELERY_ROUTES = {
        'moviebox.parse_movie': {'queue': 'info'},
        'moviebox.parse_tv': {'queue': 'info'},
        'moviebox.parse_trailer': {'queue': 'info'},
        'moviebox.download_video': {'queue': 'video'},
    }


app = celery.Celery("moviebox")
app.config_from_object(Config)
# Allow celery run as root
celery.platforms.C_FORCE_ROOT = True

headers = {"User-Agent": "Show Box", "Accept-Encoding": "gzip",
           "Host": "sbfunapi.cc", "Connection": "Keep-Alive"}

engine = create_engine(
    u"mysql://%(user)s:%(passwd)s@%(host)s:%(port)d/%(db)s" % settings.MYSQL_CONF,
    pool_size=21, encoding='utf-8'
)

logger = get_task_logger(__name__)

Session = sessionmaker(bind=engine)
session = Session()


@app.task(bind=True, max_retries=10)
def parse_movie(self, movie):
    try:
        response = requests.get(MOVIE_DETAIL_URL % movie['id'],
                                headers=headers)
    except requests.ConnectionError, exc:
        raise self.retry(exc=exc, countdown=60)
    movie_data = response.json()
    movie_data['id'] = int(movie['id'])
    movie_data['title'] = movie['title'].encode('utf-8')
    movie_data['imdb_id'] = movie['imdb_id']
    movie_data['rating'] = int(movie['rating'] or 0)
    movie_data['year'] = movie['year']
    movie_data['is_deleted'] = not bool(int(movie.get('active')))
    movie_data['update_time'] = datetime.datetime.now()

    _headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0",
        "Host": "www.imdb.com"
    }
    try:
        response = requests.get(IMDB_PAGE_URL % movie['imdb_id'],
                                headers=_headers)
    except requests.ConnectionError, exc:
        raise self.retry(exc=exc, countdown=60)
    root = html.fromstring(response.content)
    try:
        release_date = root.xpath("//div[@class='subtext']//meta[@itemprop='datePublished']/@content")[0]
        movie_data['release_time'] = datetime.datetime.strptime(release_date, "%Y-%m-%d")
    except:
        movie_data['release_time'] = None
    try:
        movie_data['play_time'] = root.xpath("//div[@class='subtext']//time[@itemprop='duration']/@datetime")[0]
    except:
        movie_data['play_time'] = None

    sql = """insert into movie(
             id, title, description, year,
             poster, rating, imdb_id, imdb_rating,
             update_time, release_time, play_time, is_deleted)
           values(
             :id, :title, :description,
             :year, :poster, :rating,
             :imdb_id, :imdb_rating,
             :update_time, :release_time, :play_time,
             :is_deleted)
          """

    try:
        session.execute(sql, movie_data)
    except IntegrityError as e:
        if e.orig[0] != 1062:
            raise e

        _sql = """update movie set
                    rating = :rating,
                    imdb_rating = :imdb_rating,
                    update_time = :update_time,
                    is_deleted = :is_deleted
                  where id = :id
               """
        session.execute(_sql, movie_data)
    else:
        # Save category
        for cat in movie['cats'].split('#'):
            sql = "insert into category(id, bind_id, media_type) values(:cate_id, :bind_id, 0)"
            if cat:
                session.execute(
                    sql,
                    {'cate_id': int(cat),
                     'bind_id': int(movie['id'])}
                )

        # Save recommend
        for rec in movie_data['recommend']:
            sql = "insert into recommend values(:rec_id, :bind_id)"
            session.execute(
                sql,
                {'rec_id': int(rec), 'bind_id': int(movie['id'])}
            )

        # Save distributors
        distributors = root.xpath("//span[@itemprop='creator' and @itemtype='http://schema.org/Organization']/a/span[@itemprop='name']/text()")
        urls = root.xpath("//span[@itemprop='creator' and @itemtype='http://schema.org/Organization']/a/@href")
        distributor_map = zip(distributors, [url.split('/company/')[1].split('?')[0] for url in urls])
        for name, imdb_id in distributor_map:
            sql = "insert into distributor_trans(name, imdb_id) values(:name, :imdb_id)"
            try:
                _rs = session.execute(
                    sql,
                    {'name': name.encode('utf-8'), 'imdb_id': imdb_id}
                )
            except IntegrityError as e:
                if e.orig[0] != 1062:
                    raise e

                _rs = session.execute("select id from distributor_trans where imdb_id = :imdb_id", {'imdb_id': imdb_id})
                dist_id = _rs.fetchone()[0]
            else:
                dist_id = _rs.lastrowid

            sql = "insert into distributor(id, bind_id) values(:dist_id, :bind_id)"
            session.execute(
                sql,
                {'dist_id': dist_id,
                 'bind_id': int(movie['id'])}
            )

        # Save directors
        directors = root.xpath("//span[@itemprop='director']/a/span[@itemprop='name']/text()")
        urls = root.xpath("//span[@itemprop='director']/a/@href")
        director_map = zip(directors,
                           [url.split('/name/')[1].split('?')[0]
                            for url in urls])
        for name, imdb_id in director_map:
            sql = "insert into director_trans(name, imdb_id) values(:name, :imdb_id)"
            try:
                _rs = session.execute(
                    sql,
                    {'name': name.encode('utf-8'), 'imdb_id': imdb_id}
                )
            except IntegrityError as e:
                if e.orig[0] != 1062:
                    raise e

                _rs = session.execute("select id from director_trans where imdb_id = :imdb_id", {'imdb_id': imdb_id})
                director_id = _rs.fetchone()[0]
            else:
                director_id = _rs.lastrowid

            sql = "insert into director(id, bind_id) values(:dire_id, :bind_id)"
            session.execute(
                sql,
                {'dire_id': director_id, 'bind_id': int(movie['id'])}
            )

        # Save actor
        actors = root.xpath("//span[@itemprop='actors']/a/span[@itemprop='name']/text()")
        urls = root.xpath("//span[@itemprop='actors']/a/@href")
        actor_map = zip(actors, [url.split('/name/')[1].split('?')[0] for url in urls])
        for name, imdb_id in actor_map:
            sql = "insert into actor_trans(name, imdb_id) values(:name, :imdb_id)"
            try:
                _rs = session.execute(
                    sql,
                    {'name': name.encode('utf-8'), 'imdb_id': imdb_id}
                )
            except IntegrityError as e:
                if e.orig[0] != 1062:
                    raise e

                _rs = session.execute("select id from actor_trans where imdb_id = :imdb_id", {'imdb_id': imdb_id})
                actor_id = _rs.fetchone()[0]
            else:
                actor_id = _rs.lastrowid

            sql = "insert into actor(id, bind_id) values(:actor_id, :bind_id)"
            session.execute(
                sql,
                {'actor_id': actor_id, 'bind_id': int(movie['id'])}
            )
    finally:
        session.commit()


@app.task(bind=True, max_retries=10)
def parse_tv(self, tv):
    for i in range(1, int(tv.get('seasons', 0))+1):
        try:
            response = requests.get(TV_DETAIL_URL % (str(i), tv['id']),
                                    headers=headers)
        except requests.ConnectionError, exc:
            raise self.retry(exc=exc, countdown=60)
        season = response.json()

        season_data = {}
        season_data['tv_id'] = int(tv['id'])
        season_data['seq'] = str(i)
        season_data['banner'] = season['banner']
        season_data['description'] = season['description'].encode('utf-8')
        season_data['update_time'] = datetime.datetime.now()

        sql = """insert into tv_season(
                   tv_id, banner, description, seq)
                 values(
                   :tv_id, :banner, :description, :seq)
              """
        try:
            _rs = session.execute(sql, season_data)
        except IntegrityError as e:
            if e.orig[0] != 1062:
                raise e

            _sql = """select id from tv_season
                        where tv_id = :tv_id and seq = :seq
                   """
            _rs = session.execute(_sql, season_data)
            season_id = _rs.fetchone()[0]
        else:
            season_id = _rs.lastrowid

        n = 1
        if type(season['thumbs']) is list:
            season['thumbs'] = {}
        for seq, pic in season['thumbs'].iteritems():
            item = {}
            item['tv_id'] = int(tv['id'])
            item['season_id'] = season_id
            item["title"] = season['titles'][seq].encode('utf-8')
            item['description'] = ''
            item['pic'] = pic
            item['seq'] = seq

            sql = """insert into tv_episode(
                       tv_id, season_id, description,
                       title, pic, seq)
                     values(
                       :tv_id, :season_id, :description,
                       :title, :pic, :seq)
                  """

            try:
                session.execute(sql, item)
            except IntegrityError as e:
                if e.orig[0] != 1062:
                    raise e
            finally:
                n += 1

    tv_data = {}
    tv_data['id'] = tv['id']
    tv_data['title'] = tv['title'].encode('utf-8')
    tv_data['description'] = ''
    tv_data['poster'] = tv['poster']
    tv_data['rating'] = int(tv['rating'] or 0)
    tv_data['banner'] = tv['banner']
    tv_data['banner_mini'] = tv['banner_mini']
    tv_data['imdb_id'] = tv['imdb_id']
    tv_data['imdb_rating'] = ''
    tv_data['update_time'] = datetime.datetime.now()
    tv_data['is_deleted'] = not bool(int(tv.get('active')))

    try:
        response = requests.get(IMDB_PAGE_URL % tv['imdb_id'],
                                headers=headers)
    except (requests.ConnectionError, requests.TooManyRedirects) as exc:
        if isinstance(exc, requests.TooManyRedirects):
            logger.error("Redirect error : %s" % tv['imdb_id'])
        raise self.retry(exc=exc, countdown=60)
    except:
        logger.error("Error imdb page: %s" % tv['imdb_id'])
        raise
    root = html.fromstring(response.content)
    try:
        release_date = root.xpath("//div[@id='titleDetails']/div/h4[text()='Release Date:']/following-sibling::text()")[0]
        tv_data['release_time'] = datetime.datetime.strptime(re.sub("\(.*\)", '', release_date).strip(), '%d %B %Y')
    except:
        tv_data['release_time'] = None

    sql = """insert into tv(
               id, title, description, poster, rating,
               banner, banner_mini, imdb_id, imdb_rating, release_time)
             values(:id, :title, :description, :poster,
               :rating, :banner, :banner_mini, :imdb_id,
               :imdb_rating, :release_time)
          """
    try:
        session.execute(sql, tv_data)
    except IntegrityError as e:
        if e.orig[0] != 1062:
            raise e

        _sql = """update tv set
                    poster = :poster,
                    rating = :rating,
                    imdb_rating = :imdb_rating,
                    release_time = :release_time,
                    is_deleted = :is_deleted
                  where id = :id
               """
        session.execute(_sql, tv_data)
    else:
        for cat in tv['cats'].split('#'):
            sql = """insert into category(id, bind_id, media_type)
                       values(:cate_id, :bind_id, 2)
                  """
            if cat:
                session.execute(
                    sql,
                    {'cate_id': int(cat), 'bind_id': int(tv['id'])}
                )
    finally:
        session.commit()


@app.task(bind=True, max_retries=10)
def parse_trailer(self, trailer):
    headers = {"Host": "sbfunapi.cc",
               "Connection": "keep-alive",
               "Accept": "*/*",
               "User-Agent": "MovieBox3/3.6.4 (iPhone; iOS 9.3.2; Scale/2.00)",
               "Accept-Language": "zh-Hans-CN;q=1, en-CN;q=0.9",
               "Accept-Encoding": "gzip, deflate",
               "Connection": "keep-alive"}
    try:
        response = requests.get(TRAILER_DETAIL_URL % trailer['id'],
                                headers=headers)
    except requests.ConnectionError, exc:
        raise self.retry(exc=exc, countdown=60)
    trailer_data = response.json()
    try:
        trailer_data['release_time'] = datetime.datetime.strptime(trailer_data['release_info'], "%d %b %Y")
    except:
        try:
            trailer_data['release_time'] = datetime.datetime.strptime(trailer_data['release_info'], "%d %B %Y")
        except:
            trailer_data['release_time'] = None

    for t in trailer_data['trailers']:
        t['trailer_id'] = trailer['id']
        vid = t['link']
        t['link'] = "video/trailer/%s.mp4" % vid
        sql = """insert into trailer_source(id, trailer_id, create_date, link)
                   values(:id, :trailer_id, :date, :link)"""
        try:
            session.execute(sql, t)
        except IntegrityError as e:
            if e.orig[0] != 1062:
                raise e
        else:
            # The link is Youtube video ID, put it into download queue.
            download_video.delay(vid)

    sql = """insert into trailer(
               id, title, description, poster, rating,
               poster_hires, release_time)
             values(:id, :title, :description, :poster,
               :rating, :poster_hires, :release_time)
          """
    trailer.update(trailer_data)
    try:
        session.execute(sql, trailer)
    except IntegrityError as e:
        if e.orig[0] != 1062:
            raise e

        # Rating must up to date
        sql = """update trailer
                   set rating = :rating
                 where id = :id
              """
        session.execute(sql, trailer)
    else:
        for cat in trailer_data['cats'].split('#'):
            sql = """insert into category(id, bind_id, media_type)
                     values(:cate_id, :bind_id, 1)
                  """
            if cat:
                session.execute(
                    sql,
                    {'cate_id': int(cat), 'bind_id': int(trailer['id'])}
                )
    finally:
        session.commit()


@app.task(bind=True, max_retries=10)
def download_video(self, vid):
    """Download Video from youtube"""
    opts = {
        u'format': u'mp4',
        u'outtmpl': u"tmp/%(id)s.%(ext)s",
    }
    try:
        with youtube_dl.YoutubeDL(opts) as ydl:
            ydl.download([u'http://www.youtube.com/watch?v=%s' % vid, ])

        files = [('file', (u"%s.mp4" % vid, open(u"tmp/%s.mp4" % vid, 'rb')))]
        response = requests.post("http://61.155.215.52:3000/upload",
                                 files=files)
        if response.content != 'ok':
            raise Exception("Upload failure!")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        if os.path.isfile(u"tmp/%s.mp4" % vid):
            os.remove(u"tmp/%s.mp4" % vid)

    return vid, response.content


# download trailer info and video from IMDB.COM
@app.task(bind=True, max_retries=10)
def download_imdb_trailer(self, movie_id):
    """Download Video from imdb.com"""
    #session = Session()

    try:
        response = requests.get(IMDB_TRAILER_URL % movie_id)
        root = html.fromstring(response.content)
        for a in root.xpath("//div[@class='search-results']/ol/li/div/a"):
            vid = a.xpath("./@data-video")[0]
            vurl = a.xpath("./@href")[0]
            vpic = a.xpath("./img/@src")[0]

            response = requests.get(vurl)
            container_url = root.xpath("//iframe[@id='video-player-container']/@src")[0].strip()
            response = requests.get(container_url)
            root = html.fromstring(response.content)
            data = root.xpath("//script[@class='imdb-player-data']/text()")[0]
            vdata = json.loads(data)
            for v in vdata['videoPlayerObject']['video']['videoInfoList']:
                if v['videoMimeType'] == 'video/mp4':
                    video_url = v['videoUrl']
                    break

            response = requests.get(video_url)
            filename = u"%s/%s.mp4" % (movie_id, vid)
            files = [('file', (filename, StringIO.StringIO(response.content))), ]
            response = requests.post("http://61.155.215.52:3000/upload",
                                     files=files)
            if response.content != 'ok':
                raise Exception("Upload failure!")

            sql = """insert into trailer_source(movie_id, imdb_id, create_date, link)
                     values(:movie_id, :imdb_id, :date, :link)
                  """
            data = {'movie_id': movie_id, 'imdb_id': vid, 'create_date': ''}
            session.execute(sql, data)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

    session.commit()

    return filename, response.content


def schedule():
    headers = {"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 6.0; Nexus 5 Build/MPA44G)"}
    response = requests.get(LIST_URL % str(random.random()), headers=headers)
    zio = StringIO.StringIO(response.content)
    zf = zipfile.ZipFile(zio)
    movies_lite = zf.read('movies_lite.json')
    movies = json.loads(movies_lite)
    for m in movies:
        parse_movie.delay(m)
    print("Movie count %d" % len(movies))

    tv_lite = zf.read('tv_lite.json')
    tv = json.loads(tv_lite)
    for t in tv:
        parse_tv.delay(t)
    print("TV count %d" % len(tv))

    headers = {"Host": "sbfunapi.cc",
               "Connection": "keep-alive",
               "Accept": "*/*",
               "User-Agent": "MovieBox3/3.6.4 (iPhone; iOS 9.3.2; Scale/2.00)",
               "Accept-Language": "zh-Hans-CN;q=1, en-CN;q=0.9",
               "Accept-Encoding": "gzip, deflate",
               "Connection": "keep-alive"}

    response = requests.get(TRAILERS_LIST_URL, headers=headers)
    trailers = response.json()
    for trailer in trailers:
        parse_trailer.delay(trailer)
    print("Trailer count %d" % len(trailers))

    # Save category names
    #session = Session()
    cates = json.loads(zf.read('cats.json'))

    for i, name in cates.items():
        sql = "insert into category_trans(id, text_name) values(:id, :name)"
        try:
            session.execute(sql, {'id': int(i), 'name': name})
        except IntegrityError as e:
            if e.orig[0] != 1062:
                raise e
            continue

    session.commit()
    zf.close()


def run():
    try:
        cmd = sys.argv[1]
    except IndexError:
        print("incorrect number of arguments\nUsage: %prog [crawl|schedule] [options] arg")
        sys.exit(1)

    if cmd == "crawl":
        task = worker.worker(app=app)
        task.execute_from_commandline(sys.argv[1:])
    elif cmd == "schedule":
        schedule()


if __name__ == '__main__':
    run()
