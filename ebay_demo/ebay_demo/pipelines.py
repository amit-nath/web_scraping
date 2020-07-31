# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import logging
import sqlite3


class SQLlitePipeline(object):

    def open_spider(self, spider):
        self.connection = sqlite3.connect("ebayuk.db")
        logging.info('SQL connection opened')
        self.c = self.connection.cursor()
        try:
            logging.info('Creating table')
            self.c.execute('''
                CREATE TABLE items(
                    name TEXT,
                    price TEXT,
                    url TEXT,
                    image_url TEXT
                )
            ''')
            self.connection.commit()
            logging.info('Table created')
        except sqlite3.OperationalError:
            logging.info('Table already exists')
            pass

    def close_spider(self, spider):
        self.connection.close()
        logging.info('SQL connection closed')

    def process_item(self, item, spider):
        self.c.execute('''
            INSERT INTO items (name,price,url,image_url) VALUES(?,?,?,?)
        ''', (
            item.get('name'),
            item.get('price'),
            item.get('url'),
            item.get('image_url'),
        ))
        self.connection.commit()
        logging.info('Query insert successful')
        return item
