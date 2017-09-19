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

months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
valid_years = [ 17, 2017, 18, 2018, 19, 2019]
_date_str = '%m/%d/%Y'

# Create your views here.

def _filter_by_price(tours, budget_min, budget_max):
    output_tours = []
    for tour in tours:
        tour_prices = tour['pricing']
        print tour_prices
        for price in tour_prices:
            value = re.sub('[^0-9]', '', tour_prices[price])
            value = int(value)
            if value >= budget_min and value <= budget_max:
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
    t = get_template('index.html')
    return HttpResponse(t.render())


def search(request):

    _collection = 'tours'

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
                    'title': 1
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
        projection['next_dates'] = 1

    # Budget:
    budget_min, budget_max = [int(x) for x in budget.split(",")]
    query['$or'] = [
                    {'pricing': {'$exists':True}},
                    {'prices' : {'$exists':True}}
                ]
    projection['pricing'] = 1

    tours_collection = _mongo_client[_db]['tours']

    print query
    print projection
    tours = tours_collection.find(query, projection)\
                .sort([('score', {"$meta" : "textScore"})])

    tours = _filter_by_price(tours, budget_min, budget_max)

    if use_dates:
        tours = _filter_by_dates(tours, dates)

    response_text = "\n\n".join([str(tour) for tour in tours])
    print response_text

    return HttpResponse(response_text)