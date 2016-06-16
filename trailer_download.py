# coding:utf-8
import os

import tornado.ioloop
import tornado.web


BASE = "/data0/androidmoviebox/"


class UploadFileHandler(tornado.web.RequestHandler):
    def post(self):
        file_metas = self.request.files['file']
        for meta in file_metas:
            filename = meta['filename']
            filepath = os.path.join(BASE, filename)
            with open(filepath, 'wb') as up:
                up.write(meta['body'])

            self.write('finished!')


app = tornado.web.Application([
    (r'/upload', UploadFileHandler),
])


if __name__ == '__main__':
    app.listen(3000)
    tornado.ioloop.IOLoop.instance().start()
