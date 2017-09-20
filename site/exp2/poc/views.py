# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse

from django.template.loader import get_template

# FIXME: Fugly but okay for now

import re
from datetime import datetime as dt

from pymongo import MongoClient
_mongo_client = MongoClient()
_db = 'test'
CITIES = 'cities'
TOURS = 'tours'

months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
            'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
valid_years = [ 17, 2017, 18, 2018, 19, 2019]
_date_str = '%m/%d/%Y'

# Create your views here.

def _filter_by_price(tours, budget_min, budget_max):
    output_tours = []
    for tour in tours:
        tour_prices = tour['pricing']
        for price in tour_prices:
            values = []
            if isinstance(tour_prices[price], dict):
                for p in tour_prices[price]:
                    value = tour_prices[price][p]
                    values.append(value)
            else:
                value = tour_prices[price]
                values = [value]
            value_found = False
            for v in values:
                try:
                    v = re.sub(r'[^0-9]', '', v)
                    value = int(v)
                except ValueError:
                    value = 0
                if value >= budget_min and value <= budget_max:
                    print value
                    value_found = True
                    break
            if value_found:
                output_tours.append(tour)
                break

    return output_tours

def _filter_by_dates(tours, dates):

    output_tours = []

    for tour in tours:
        for start, end in tour['next_dates']:
            start_month = dt.strptime(start, _date_str).strftime('%b')
            start_year = dt.strptime(start, _date_str).strftime('%y')
            if '-'.join([start_month, start_year]) in dates:
                output_tours.append(tour)
                break
            end_month = dt.strptime(end, _date_str).strftime('%b')
            end_year = dt.strptime(end, _date_str).strftime('%y')
            if '-'.join([end_month, end_year]) in dates:
                output_tours.append(tour)
                break
    return output_tours

def index(request):

    cities_collection = _mongo_client[_db][CITIES]
    tours_collection = _mongo_client[_db][TOURS]

    cities = cities_collection.find({}, {'city_name':1})

    out_cities = []
    for city in cities:
        name = city['city_name']
        tours_count = tours_collection.find({'cities': name}).count()
        out_cities.append({'name': name, 'count' : tours_count})
    out_cities = sorted(out_cities, key=lambda x: x['count'], reverse=True)
    t = get_template('index.html')
    return HttpResponse(t.render(context={'cities': out_cities}))


def search(request):

    dates = request.GET.get('dates')
    budget = request.GET.get('budget')
    q = request.GET.get('searchq')

    # first get all tours that match search query.
    query = {}
    if q :
        q = re.sub(r'[^a-zA-Z0-9\s]', '', q)
        query['$text'] = {'$search' : q}

    projection = {
                    'score': {'$meta': "textScore"},
                    'title': 1,
                    'type': 1,
                    'next_dates': 1,
                    'pricing': 1,
                    'overview': 1
                }

    # FIXME : separate to a different function
    use_dates = False
    if dates: # non-empty dates
        dates = dates.split(',')
        for date in dates:
            try:
                month, year = date.split('-')
                if month.lower() not in months:
                    use_dates = False
                if int(year) not in valid_years:
                    use_dates = False
                use_dates = True
            except (ValueError, TypeError):
                use_dates = False
                break
    if use_dates:
        query['next_dates'] = {'$exists': True}

    # Budget:
    budget_min, budget_max = [int(x) for x in budget.split(",")]

    tours_collection = _mongo_client[_db]['tours']

    tours = tours_collection.find(query, projection)\
                .sort([('score', {"$meta" : "textScore"})])

    tours = _filter_by_price(tours, budget_min, budget_max)

    if use_dates:
        tours = _filter_by_dates(tours, dates)

    #response_text = "\n\n".join([str(tour) for tour in tours])

    t = get_template('search.html')

    return HttpResponse(t.render(context={'tours':tours}))
