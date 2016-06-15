# coding:utf-8
import json
import random
import zipfile
import StringIO
import datetime

import celery
import requests
import MySQLdb
import youtube_dl
from lxml import html

import settings


LIST_URL = "http://sbfunapi.cc/data/data_en.zip?q=%s"
TRAILERS_LIST_URL = "http://sbfunapi.cc/api/serials/trailers_movies/?feed=popular"
TRAILER_DETAIL_URL = "http://sbfunapi.cc/api/serials/trailers/?id=%s"
MOVIE_DETAIL_URL = "http://sbfunapi.cc/api/serials/movie_details/?id=%s"
TV_DETAIL_URL = "http://sbfunapi.cc/api/serials/es/?season=%s&id=%s"

IMDB_PAGE_URL = "http://www.imdb.com/title/%s/"

db = MySQLdb.connect(**settings.MYSQL_CONF)
c = celery.Celery("moviebox", broker="redis://:%(password)s@%(host)s:%(port)d/%(db)d" % settings.REDIS_CONF)
# Allow celery run as root
celery.platforms.C_FORCE_ROOT = True

headers = {"User-Agent": "Show Box", "Accept-Encoding": "gzip",
           "Host": "sbfunapi.cc", "Connection": "Keep-Alive"}


class Transaction(object):
    def __init__(self, db=None):
        self.db = db

    def __enter__(self):
        self.cursor = self.db.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type:
            self.db.rollback()
        else:
            self.db.commit()

        self.cursor.close()


@c.task(bind=True, max_retries=10)
def parse_movie(self, movie):
    cursor = db.cursor()
    cursor.execute("select id from movie where id = %s", movie['id'])
    if cursor.fetchone():
        return "exists."

    try:
        response = requests.get(MOVIE_DETAIL_URL % movie['id'], headers=headers)
    except requests.ConnectionError, exc:
        raise self.retry(exc=exc, countdown=60)
    movie_data = response.json()
    movie_data['id'] = int(movie['id'])
    movie_data['title'] = movie['title']
    movie_data['imdb_id'] = movie['imdb_id']
    movie_data['rating'] = int(movie['rating'] or 0)
    movie_data['year'] = movie['year']
    movie_data['is_deleted'] = False
    movie_data['update_time'] = datetime.datetime.now()

    _headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0",
        "Host": "www.imdb.com"
    }
    try:
        response = requests.get(IMDB_PAGE_URL % movie['imdb_id'], headers=_headers)
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

    with Transaction(db) as cursor:
        sql = "insert into movie( \
                 id, title, description, year, \
                 poster, rating, imdb_id, imdb_rating, \
                 update_time, release_time, play_time, is_deleted) \
               values(\
                 %(id)s, %(title)s, %(description)s, \
                 %(year)s, %(poster)s, %(rating)s, \
                 %(imdb_id)s, %(imdb_rating)s, \
                 %(update_time)s, %(release_time)s, %(play_time)s, \
                 %(is_deleted)s)"

        try:
            cursor.execute(sql, movie_data)
        except db.IntegrityError as e:
            if e[0] != 1062:
                raise e

            _sql = """update movie set
                        description = %(description)s,
                        title = %(title)s,
                        year = %(year)s,
                        rating = %(rating)s,
                        poster = %(poster)s,
                        imdb_rating = %(imdb_rating)s
                        update_time = %(update_time)s
                      where id = %(id)s
                   """
            cursor.execute(_sql, movie_data)
        else:
            # Save category
            for cat in movie['cats'].split('#'):
                sql = "insert into category(id, bind_id, media_type) values(%s, %s, %s)"
                if cat:
                    cursor.execute(sql, (int(cat), int(movie['id']), 0))

            # Save recommend
            for rec in movie_data['recommend']:
                sql = "insert into recommend values(%s, %s)"
                cursor.execute(sql, (int(rec), int(movie['id'])))

            # Save distributors
            distributors = root.xpath("//span[@itemprop='creator' and @itemtype='http://schema.org/Organization']/a/span[@itemprop='name']/text()")
            urls = root.xpath("//span[@itemprop='creator' and @itemtype='http://schema.org/Organization']/a/@href")
            distributor_map = zip(distributors, [url.split('/company/')[1].split('?')[0] for url in urls])
            for m in distributor_map:
                sql = "insert into distributor_trans(name, imdb_id) values(%s, %s)"
                try:
                    cursor.execute(sql, m)
                except db.IntegrityError as e:
                    if e[0] != 1062:
                        raise e

                    cursor.execute("select id from distributor_trans where imdb_id = %s", (m[1], ))
                    dist_id = cursor.fetchone()[0]
                else:
                    dist_id = cursor.lastrowid

                sql = "insert into distributor(id, bind_id) values(%s, %s)"
                cursor.execute(sql, (dist_id, int(movie['id'])))

            # Save directors
            directors = root.xpath("//span[@itemprop='director']/a/span[@itemprop='name']/text()")
            urls = root.xpath("//span[@itemprop='director']/a/@href")
            director_map = zip(directors, [url.split('/name/')[1].split('?')[0] for url in urls])
            for m in director_map:
                sql = "insert into director_trans(name, imdb_id) values(%s, %s)"
                try:
                    cursor.execute(sql, m)
                except db.IntegrityError as e:
                    if e[0] != 1062:
                        raise e

                    cursor.execute("select id from director_trans where imdb_id = %s", (m[1], ))
                    director_id = cursor.fetchone()[0]
                else:
                    director_id = cursor.lastrowid

                sql = "insert into director(id, bind_id) values(%s, %s)"
                cursor.execute(sql, (director_id, int(movie['id'])))

            # Save actor
            actors = root.xpath("//span[@itemprop='actors']/a/span[@itemprop='name']/text()")
            urls = root.xpath("//span[@itemprop='actors']/a/@href")
            actor_map = zip(actors, [url.split('/name/')[1].split('?')[0] for url in urls])
            for m in actor_map:
                sql = "insert into actor_trans(name, imdb_id) values(%s, %s)"
                try:
                    cursor.execute(sql, m)
                except db.IntegrityError as e:
                    if e[0] != 1062:
                        raise e

                    cursor.execute("select id from actor_trans where imdb_id = %s", (m[1], ))
                    actor_id = cursor.fetchone()[0]
                else:
                    actor_id = cursor.lastrowid

                sql = "insert into actor(id, bind_id) values(%s, %s)"
                cursor.execute(sql, (actor_id, int(movie['id'])))


@c.task(bind=True, max_retries=10)
def parse_tv(self, tv):
    with Transaction(db) as cursor:
        for i in range(1, int(tv.get('seasons', 1))+1):
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
            season_data['description'] = season['description']
            season_data['update_time'] = datetime.datetime.now()

            sql = """insert into tv_season(
                       tv_id, banner, description, seq)
                     values(%(tv_id)s, %(banner)s, %(description)s, %(seq)s)
                  """
            try:
                cursor.execute(sql, season_data)
            except db.IntegrityError as e:
                if e[0] != 1062:
                    raise e

                _sql = """update tv_season
                            set banner = %s,
                            set description = %s
                          where tv_id = %s and seq = %s
                       """
                cursor.execute(_sql, season_data)

                _sql = """select id from tv_seson
                         where tv_id = %(tv_id)s and seq = %(seq)s
                      """
                cursor.execute(_sql, season_data)
                _data = cursor.fetchone()
                season_id = _data[0]
            else:
                season_id = cursor.lastrowid

            n = 1
            for seq, pic in season['thumbs'].iteritems():
                item = {}
                item['tv_id'] = int(tv['id'])
                item['season_id'] = season_id
                item["title"] = season['titles'][seq]
                item['description'] = ''
                item['pic'] = pic
                item['seq'] = seq

                sql = """insert into tv_episode(
                           tv_id, season_id, description,
                           title, pic, seq)
                         values(
                           %(tv_id)s, %(season_id)s, %(description)s,
                           %(title)s, %(pic)s, %(seq)s)
                      """

                try:
                    cursor.execute(sql, item)
                except db.IntegrityError as e:
                    if e[0] != 1062:
                        raise e
                finally:
                    n += 1

        tv_data = {}
        tv_data['id'] = tv['id']
        tv_data['title'] = tv['title']
        tv_data['description'] = ''
        tv_data['poster'] = tv['poster']
        tv_data['rating'] = int(tv['rating'] or 0)
        tv_data['banner'] = tv['banner']
        tv_data['banner_mini'] = tv['banner_mini']
        tv_data['imdb_id'] = tv['imdb_id']
        tv_data['imdb_rating'] = ''
        tv_data['update_time'] = datetime.datetime.now()

        sql = """insert into tv(
                   id, title, description, poster, rating,
                   banner, banner_mini, imdb_id, imdb_rating)
                 values(%(id)s, %(title)s, %(description)s, %(poster)s,
                   %(rating)s, %(banner)s, %(banner_mini)s, %(imdb_id)s,
                   %(imdb_rating)s)
              """
        try:
            cursor.execute(sql, tv_data)
        except db.IntegrityError as e:
            if e[0] != 1062:
                raise e

            _sql = """update tv set
                        title = %(title)s,
                        description = %(description)s,
                        poster = %(poster)s,
                        rating = %(rating)s,
                        banner = %(banner)s,
                        banner_mini = %(banner_mini)s,
                        imdb_rating = %(imdb_rating)s
                      where id = %(id)s
                   """
            cursor.execute(_sql, tv_data)
        else:
            for cat in tv['cats'].split('#'):
                sql = "insert into category(id, bind_id, media_type) values(%s, %s, %s)"
                if cat:
                    cursor.execute(sql, (int(cat), int(tv['id']), 2))


@c.task(bind=True, max_retries=10)
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

    with Transaction(db) as cursor:
        for t in trailer_data['trailers']:
            t['trailer_id'] = trailer['id']
            vid = t['link']
            t['link'] = "video/trailer/%s.mp4" % vid
            sql = """insert into trailer_source(id, trailer_id, create_date, link)
                       values(%(id)s, %(trailer_id)s, %(date)s, %(link)s)"""
            try:
                cursor.execute(sql, t)
            except db.IntegrityError as e:
                if e[0] != 1062:
                    raise e
            else:
                # The link is Youtube video ID, put it into download queue.
                download_video.delay(vid)

        sql = """insert into trailer(
                   id, title, description, poster, rating,
                   poster_hires, release_time)
                 values(%(id)s, %(title)s, %(description)s, %(poster)s,
                   %(rating)s, %(poster_hires)s, %(release_time)s)
              """
        trailer.update(trailer_data)

        try:
            cursor.execute(sql, trailer)
        except db.IntegrityError as e:
            if e[0] != 1062:
                raise e
        else:
            for cat in trailer_data['cats'].split('#'):
                sql = "insert into category(id, bind_id, media_type) values(%s, %s, %s)"
                if cat:
                    cursor.execute(sql, (int(cat), int(trailer['id']), 1))


def download_video(self, vid):
    """Download Video from youtube"""
    opts = {
        'format': 'mp4',
        'outtmpl': "/data0/androidmoviebox/video/trailer/%(id)s.%(ext)s",
    }
    with youtube_dl.YoutubeDL(opts) as ydl:
        ydl.download(['http://www.youtube.com/watch?v=%s' % vid, ])


def run():
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
    cates = json.loads(zf.read('cats.json'))
    with Transaction(db) as cursor:
        for i, name in cates.items():
            sql = "insert into category_trans(id, text_name) values(%s, %s)"
            cursor.execute(sql, (int(i), name))

    zf.close()

if __name__ == '__main__':
    run()
