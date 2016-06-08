# coding:utf-8
from __future__ import unicode_literals

import os

import MySQLdb
import celery
from boto.s3.connection import S3Connection
import youtube_dl

conn = S3Connection()
bucket = conn.get_bucket('androidpackage')
db = MySQLdb.connect(host='192.168.2.20', user='moviebox',
                     passwd='moviebox', db='moviebox')

c = celery.Celery("video_dl", broker="redis://:appvvcom@192.168.2.20/2")


@c.task
def download(vid):
    opts = {
        'format': 'mp4',
        'outtmpl': "tmp/%(id)s.%(ext)s",
    }
    with youtube_dl.YoutubeDL(opts) as ydl:
        ydl.download(['http://www.youtube.com/watch?v=%s' % vid, ])

    key = bucket.new_key("video/trailer/%s.mp4" % vid)
    key.set_contents_from_filename("tmp/%s.mp4" % vid)
    key.close()

    os.remove("tmp/%s.mp4" % vid)


if __name__ == '__main__':
    cursor = db.cursor()
    cursor.execute("select link from trailer_source")
    data = cursor.fetch_all()
    for link, in data:
        download.delay(link)
