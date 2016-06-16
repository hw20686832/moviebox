# coding:utf-8
import os
import datetime
import hashlib

import MySQLdb
from flask import Flask, request

import settings

app = Flask(__name__)
app.config['TRAILER_FOLDER'] = "/data0/androidmoviebox/video/trailer/"
app.config['PACKAGE_FOLDER'] = "/data0/androidmoviebox/package"

db = MySQLdb.connect(**settings.MYSQL_CONF)


@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = file.filename
            file.save(os.path.join(app.config['TRAILER_FOLDER'], filename))

            return "ok"


@app.route('/upgrade', methods=['POST'])
def upgrade():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = file.filename
            file.save(os.path.join(app.config['PACKAGE_FOLDER'], filename))

            cursor = db.cursor()
            sql = """insert into app_upgrade
                       (url, md5, version_code, upgrade_info, release_time)
                     values
                       (%s, %s, %s, %s, %s)
                  """
            url = os.path.join('package', filename)
            md5 = hashlib.md5(file.read()).hexdigest()
            version_code = request.args.get('version_code')
            upgrade_info = request.args.get('upgrade_info')
            release_time = datetime.datetime.now()
            cursor.execute(sql, (url, md5, version_code, upgrade_info, release_time))
            db.commit()

            return "ok"


if __name__ == "__main__":
    app.run('0.0.0.0', 3000)
