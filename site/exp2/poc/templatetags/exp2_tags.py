from django import template
from collections import OrderedDict
register = template.Library()


@register.filter('mongo_id')
def mongo_id(val):
    return str(val['_id'])


@register.filter('sort_itinerary')
def sort_itinerary(itinerary_dict):

    new_dict = OrderedDict()
    keys = sorted(itinerary_dict, key=lambda x: int(x.split("_")[1]))
    for key in keys:
        new_dict[key] = itinerary_dict[key]
    return new_dict.iteritems()
