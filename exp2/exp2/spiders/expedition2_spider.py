"""
scraps expedition2 site and inserts in mongodb
"""

import scrapy

import time
import sys
import re

from pymongo import MongoClient
import json


class Expedition2ToursSpider(scrapy.Spider):

    def _parse_cities(self, response, selector):
        """
        parses a given selector for cities and returns a dictionary of cities
        key: city, value: url
        """
        selectors = response.css(selector)
        tour_city_names = map(lambda x: x.css('center::text').extract_first().\
                                    strip().lower(), selectors)
        tour_city_urls = map(lambda x: x.css('a::attr(href)').\
                                    extract_first().strip(), selectors)

        #tour_cities_dict = dict(zip(tour_city_names, tour_city_tnails))

        return tour_city_names, tour_city_urls


    def _parse_duration_title(self, response):
        # FIXME: May be we should send a selector?
        # Get the duration and title
        heading = response.css('#indinnerbanner #package_abs '\
                                '.bottomStrip .head')
        duration = heading.css('span::text').extract_first()
        if duration is None:
            duration = response.css('div.bottomStrip p span::text').extract_first()
        duration = duration.split("/")
        days = int(duration[0].strip().split()[0])
        nights = int(duration[1].strip().split()[0])

        duration = (days, nights)

        # title
        title = heading.css('.head::text').extract_first()
        if title is None:
            title = response.css('div.bottomStrip p::text').extract_first()

        title = title.strip().capitalize()

        return duration, title


    def _parse_overview(self, response, selector):

        overview = response.css(selector)
        ## get text of all descendents
        overview = overview[0]
        overview_text = '\n'.join(map(lambda x:x,
                            filter(lambda x: len(x.strip()) > 0,
                                overview.root.itertext())
                        ))

        overview_text = re.sub(r'[^0-9a-zA-Z\-."\'\s\r]', '', overview_text)
        return overview_text

    def _parse_tour_images(self, response):

        images = response.css('div.ws_images > ul > li')
        image_urls  = []
        for image in images:
            image_urls.append(image.css('img::attr(src)').extract_first())
            image_urls = [re.sub(r'^\.\.', r'https://expedition2india.com', u) \
                                for u in image_urls]

        return image_urls

    def parse_city(self, response):

        city_dict = {}
        # Get the overview
        overview = response.css('td.normal_content').pop()
        # remove non-ascii
        overview_text = re.sub(r'[^\x00-\x7f]+', ' ',
                                ''.join(overview.root.itertext()).strip())
        overview_text = re.sub(r'[ ]+', ' ', overview_text)

        city_dict['overview'] = overview_text
        city_dict['city_name'] = response.request.meta['city_name']

        # get the image
        style = response.css('#indinnerbanner::attr(style)').extract_first()
        url = re.search(r'background:url\((.*)\).*', style).group(1)
        city_dict['image_urls'] = [url]

        yield city_dict

class IndependentToursSpider(Expedition2ToursSpider):
    name = 'independent_tours'

    start_urls = ['https://expedition2india.com/independent-india-tours/']

    def _parse_pricing(self, response):
        tour_prices = {}
        price_selectors = response.css('.pricingbox.pricingava .availbilitybox '\
                                '.mytrunk')

        for price in price_selectors:
            price_class = price.css('h4::text').extract_first().lower()\
                                    .strip().replace(' ', '_')
            price_list = price.css('p::text').extract()
            double_o = price_list[1]
            single_o = price_list[3]
            tour_prices[price_class] = {'double': double_o, 'single': single_o}

        return tour_prices

    def _parse_itinerary(self, response):
        itinerary = response.css('article.itinerarysection')
        days_details = itinerary.css('div > div.left div.itinerarytext')

        itinerary_dict = {}
        day_num = 1

        prev_hotel = None
        for day in days_details:
            day_key = 'day_' + str(day_num)
            activity = "\n".join(map(lambda x:x.strip(),
                                    day.css('p::text').extract()))

            hotel = day.css('#hotels_div a')
            if hotel:
                hotel_url = hotel.css('a::attr(href)').extract_first()
                hotel_name = hotel.css('a::text').extract_first()
                hotel_class = re.search(r'\((.*)\)', hotel_name).\
                                                group(1).strip().lower()
                hotel_name = re.split(r'\(.*\)', hotel_name)[0].\
                                                strip().capitalize()

                hotel_dict = {'name': hotel_name,
                              'class': hotel_class,
                              'url': hotel_url}

                prev_hotel = hotel_dict

            itinerary_dict[day_key] = { 'activity' : activity, 'hotel': prev_hotel}
            day_num += 1

        return itinerary_dict

    def parse(self, response):

        tours = response.css('article ul.tour li')

        for tour in tours:
            tour_detail_url = tour.css('a::attr(href)').extract_first()
            tour_thumbnail_url = tour.css('img::attr(src)').extract_first()
            request = scrapy.Request(tour_detail_url, callback=self.parse_tour)
            request.meta['tour_thumbnail_url'] = tour_thumbnail_url
            yield request

    def parse_tour(self, response):

        tour_dict = {}

        tour_dict['type'] = 'independent'
        #duration and title
        duration, title = self._parse_duration_title(response)
        tour_dict['duration']  = duration
        tour_dict['title'] = title

        # overview
        selector = 'div.overviewtext > div > div.overviewtext'
        overview = self._parse_overview(response, selector)
        tour_dict['overview'] = overview

        # cities
        selector = 'ul#carousel > li'
        tour_cities, tour_city_urls = self._parse_cities(response, selector)
        tour_dict['cities'] = tour_cities

        for city_name, city_url in zip(tour_cities, tour_city_urls):
            request = scrapy.Request(city_url, callback=self.parse_city)
            request.meta['city_name'] = city_name
            yield request

        # pricing
        tour_prices = self._parse_pricing(response)
        tour_dict['pricing'] = tour_prices

        # itinerary
        itinerary_dict = self._parse_itinerary(response)
        tour_dict['itinerary'] = itinerary_dict

        tour_dict['thumbnail_url'] = response.request.meta['tour_thumbnail_url']

        tour_dict['image_urls'] = self._parse_tour_images(response)

        yield tour_dict
        #entry = self.db.tours.insert_one(tour_dict)

class GroupTourSpider(Expedition2ToursSpider):

    name = 'group_tours'
    start_urls = ['https://expedition2india.com/group-tours/']

    def _parse_pricing(self, response):

        price_list = response.css('.mytrunk.opendates p::text').extract()
        double_o = price_list[1].strip()
        single_o = price_list[3].strip()
        tariffs = {'double': double_o, 'single': single_o}

        return tariffs

    def _parse_dates(self, response):

        # we have to follow very clumsy way - but can't help
        tour_dates = []
        all_dates = response.css('.mytrunk.opendates::text').extract()
        for date in all_dates:
            if len(date.strip()):
                start_date, end_date = date.strip().split("-")
                start_date = start_date.strip()
                end_date = end_date.strip()
                tour_dates.append((start_date, end_date))
        return tour_dates

    def _parse_itinerary(self, response):

        days_details = response.css('div.overviewtext > div > div.left')

        itinerary_dict = {}
        day_num = 1

        prev_hotel = None
        for day in days_details:
            day_key = 'day_' + str(day_num)
            activity = '\n'.join([x.strip() for x in day.root.itertext()
                                            if len(x.strip()) > 0])

            hotel = day.css('#hotels_div a')
            if hotel:
                hotel_url = hotel.css('a::attr(href)').extract_first()
                hotel_name = hotel.css('a::text').extract_first()

                hotel_dict = {'name': hotel_name,
                              'url': hotel_url}

                prev_hotel = hotel_dict

            itinerary_dict[day_key] = { 'activity' : activity, 'hotel': prev_hotel}
            day_num += 1

        return itinerary_dict

    def parse(self, response):

        tours = response.css('ul.grouptour li')

        for tour in tours:
            tour_detail_url = tour.css('a::attr(href)').extract_first()
            tour_thumbnail_url = tour.css('img::attr(src)').extract_first()
            request = scrapy.Request(tour_detail_url, callback=self.parse_tour)
            request.meta['tour_thumbnail_url'] = tour_thumbnail_url
            yield request

    def parse_tour(self, response):

        tour_dict = {}
        tour_dict['type'] = 'group'

        # duration and title
        duration, title = self._parse_duration_title(response)
        tour_dict['duration'] = duration
        tour_dict['title'] = title

        # overview
        selector = 'div.overviewtext > div > div '
        overview = self._parse_overview(response, selector)
        tour_dict['overview'] = overview

        # cities
        selector = ('ul#carousel > li')
        tour_cities, tour_city_urls = self._parse_cities(response, selector)
        tour_dict['cities'] = tour_cities

        for city_name, city_url in zip(tour_cities, tour_city_urls):
            request = scrapy.Request(city_url, callback=self.parse_city)
            request.meta['city_name'] = city_name
            yield request

        # parse prices
        tour_prices = self._parse_pricing(response)
        tour_dict['pricing'] = tour_prices

        # parse dates
        tour_dates = self._parse_dates(response)
        tour_dict['next_dates'] = tour_dates

        # itinerary
        itinerary_dict = self._parse_itinerary(response)
        tour_dict['itinerary'] = itinerary_dict

        tour_dict['thumbnail_url'] = response.request.meta['tour_thumbnail_url']

        tour_dict['image_urls'] = self._parse_tour_images(response)

        yield tour_dict

