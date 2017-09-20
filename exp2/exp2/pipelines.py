# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo

class Exp2MongoPipeline(object):

    mongo_collection = 'tours'
    mongo_db = 'test'

    def open_spider(self, spider):
        self.client = pymongo.MongoClient()
        self.db = self.client[self.mongo_db]


    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):

        if item.has_key('itinerary'):
            collection = 'tours'
        elif item.has_key('city_name'):
            collection = 'cities'

        collection = self.db[collection]
        collection.insert_one(dict(item))
        return item

