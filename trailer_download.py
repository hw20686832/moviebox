# coding:utf-8
import celery
import youtube_dl

import settings


c = celery.Celery("trailer_download", broker="redis://:%(password)s@%(host)s:%(port)d/2" % settings.REDIS_CONF)


@c.task(bind=True, max_retries=3)
def download_video(self, vid):
    """Download Video from youtube"""
    opts = {
        'proxy': 'socks5://127.0.0.1:1080/',
        'format': 'mp4',
        'outtmpl': "/data0/androidmoviebox/video/trailer/%(id)s.%(ext)s",
    }
    with youtube_dl.YoutubeDL(opts) as ydl:
        ydl.download(['http://www.youtube.com/watch?v=%s' % vid, ])
