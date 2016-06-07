#!/usr/bin/env python
# coding:utf-8
import sys

import MySQLdb


db = MySQLdb.connect(host='192.168.2.20', user='moviebox',
                     passwd='moviebox', db='moviebox')


def truncate(*tables):
    cursor = db.cursor()
    for table in tables:
        sql = "delete from %s" % table
        cursor.execute(sql)
    db.commit()


if __name__ == '__main__':
    arg_tables = sys.argv[1:]
    all_tables = ['category', 'category_trans', 'movie',
                  'recommend', 'trailer', 'trailer_source',
                  'tv', 'tv_episode', 'tv_season']

    truncate(*(arg_tables or all_tables))
