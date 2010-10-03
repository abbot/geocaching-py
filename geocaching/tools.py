# -*- encoding: utf-8 -*-

def cache(gpx):
    try:
        return gpx.xpath('//*[local-name()="cache"]')[0]
    except TypeError:
        return None

def geocode(gpx):
    try:
        geocache = cache(gpx)
        return geocache.xpath('../*[local-name()="name"]')[0].text
    except (AttributeError, TypeError):
        return None
