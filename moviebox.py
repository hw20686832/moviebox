# coding:utf-8
import json
import random
import zipfile
import StringIO

import celery
import requests
import MySQLdb

from video_dl import download


LIST_URL = "http://sbfunapi.cc/data/data_en.zip?q=%s"
TRAILERS_LIST_URL = "http://sbfunapi.cc/api/serials/trailers_movies/?feed=popular"
TRAILER_DETAIL_URL = "http://sbfunapi.cc/api/serials/trailers/?id=%s"
MOVIE_DETAIL_URL = "http://sbfunapi.cc/api/serials/movie_details/?id=%s"
TV_DETAIL_URL = "http://sbfunapi.cc/api/serials/es/?season=%s&id=%s"


db = MySQLdb.connect(host='192.168.2.20', user='moviebox',
                     passwd='moviebox', db='moviebox')
c = celery.Celery("moviebox", broker="redis://:appvvcom@192.168.2.20/1")

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


@c.task
def parse_movie(movie):
    response = requests.get(MOVIE_DETAIL_URL % movie['id'], headers=headers)
    movie_data = response.json()
    movie_data['id'] = int(movie['id'])
    movie_data['title'] = movie['title']
    movie_data['imdb_id'] = movie['imdb_id']
    movie_data['rating'] = int(movie['rating'] or 0)
    movie_data['year'] = movie['year']
    movie_data['is_deleted'] = False

    with Transaction(db) as cursor:
        sql = "insert into movie( \
                 id, title, description, year, \
                 poster, rating, imdb_id, imdb_rating, is_deleted) \
               values(\
                 %(id)s, %(title)s, %(description)s, \
                 %(year)s, %(poster)s, %(rating)s, \
                 %(imdb_id)s, %(imdb_rating)s, %(is_deleted)s)"
        cursor.execute(sql, movie_data)

        for cat in movie['cats'].split('#'):
            sql = "insert into category(id, bind_id, media_type) values(%s, %s, %s)"
            if cat:
                cursor.execute(sql, (int(cat), int(movie['id']), 0))

        for rec in movie_data['recommend']:
            sql = "insert into recommend values(%s, %s)"
            cursor.execute(sql, (int(rec), int(movie['id'])))


@c.task
def parse_tv(tv):
    with Transaction(db) as cursor:
        for i in range(1, int(tv.get('seasons', 1))+1):
            response = requests.get(TV_DETAIL_URL % (str(i), tv['id']),
                                    headers=headers)
            season = response.json()

            season_data = {}
            season_data['tv_id'] = int(tv['id'])
            season_data['seq'] = str(i)
            season_data['banner'] = season['banner']
            season_data['description'] = season['description']

            sql = """insert into tv_season(
                       tv_id, banner, description, seq)
                     values(%(tv_id)s, %(banner)s, %(description)s, %(seq)s)
                  """
            season_id = cursor.execute(sql, season_data)

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
                cursor.execute(sql, item)
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
        sql = """insert into tv(
                   id, title, description, poster, rating,
                   banner, banner_mini, imdb_id, imdb_rating)
                 values(%(id)s, %(title)s, %(description)s, %(poster)s,
                   %(rating)s, %(banner)s, %(banner_mini)s, %(imdb_id)s,
                   %(imdb_rating)s)
              """
        cursor.execute(sql, tv_data)

        for cat in tv['cats'].split('#'):
            sql = "insert into category(id, bind_id, media_type) values(%s, %s, %s)"
            if cat:
                cursor.execute(sql, (int(cat), int(tv['id']), 2))


@c.task
def parse_trailer(trailer):
    headers = {"Host": "sbfunapi.cc",
               "Connection": "keep-alive",
               "Accept": "*/*",
               "User-Agent": "MovieBox3/3.6.4 (iPhone; iOS 9.3.2; Scale/2.00)",
               "Accept-Language": "zh-Hans-CN;q=1, en-CN;q=0.9",
               "Accept-Encoding": "gzip, deflate",
               "Connection": "keep-alive"}
    response = requests.get(TRAILER_DETAIL_URL % trailer['id'],
                            headers=headers)
    trailer_data = response.json()

    with Transaction(db) as cursor:
        for t in trailer_data['trailers']:
            t['trailer_id'] = trailer['id']
            sql = """insert into trailer_source(id, trailer_id, create_date, link)
                       values(%(id)s, %(trailer_id)s, %(date)s, %(link)s)"""
            cursor.execute(sql, t)
            # The link is Youtube video ID, put it into download queue.
            # Download task queue based on celery yet.
            download.apply_async((t['link'], ))

        sql = """insert into trailer(
                   id, title, description, poster, rating,
                   poster_hires, release_info)
                 values(%(id)s, %(title)s, %(description)s, %(poster)s,
                   %(rating)s, %(poster_hires)s, %(release_info)s)
              """
        trailer.update(trailer_data)
        cursor.execute(sql, trailer)

        for cat in trailer_data['cats'].split('#'):
            sql = "insert into category(id, bind_id, media_type) values(%s, %s, %s)"
            if cat:
                cursor.execute(sql, (int(cat), int(trailer['id']), 1))


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

    cates = json.loads(zf.read('cats.json'))
    with Transaction(db) as cursor:
        for i, name in cates.items():
            sql = "insert into category_trans(id, text_name) values(%s, %s)"
            cursor.execute(sql, (int(i), name))

    zf.close()

if __name__ == '__main__':
    run()
