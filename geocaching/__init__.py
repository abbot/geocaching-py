# -*- encoding: utf-8 -*-

import atexit
import cgi
from ConfigParser import SafeConfigParser
import cookielib
from cStringIO import StringIO
import json
import os
import re
from urllib import urlencode
import urllib2
from urlparse import urljoin, urlparse, urlunparse
import sys

from BeautifulSoup import BeautifulSoup
from lxml import etree, html

import tools

__all__ = ['Geo', 'GeoCache']

def extract_username(et):
    span = et.find('//span[@class="Success"]/strong')
    if span is not None:
        return span.text
    return None

attribute_map = {
    "dog": (1, "Dogs"),
    "dogs": (1, "Dogs allowed"),
    "fee": (2, "Access or parking fee"),
    "rappelling": (3, "Climbing gear"),
    "boat": (4, "Boat"),
    "scuba": (5, "Scuba gear"),
    "kids": (6, "Recommended for kids"),
    "onehour": (7, "Takes less than an hour"),
    "scenic": (8, "Scenic view"),
    "hiking": (9, "Significant hike"),
    "climbing": (10, "Difficult climbing"),
    "wading": (11, "May require wading"),
    "swimming": (12, "May require swimming"),
    "available": (13, "Available at all times"),
    "night": (14, "Recommended at night"),
    "winter": (15, "Available during winter"),
    "poisonoak": (17, "Poison plants"),
    "snakes": (18, "Snakes"),
    "ticks": (19, "Ticks"),
    "mines": (20, "Abandoned mines"),
    "cliff": (21, "Cliff / falling rocks"),
    "hunting": (22, "Hunting"),
    "danger": (23, "Dangerous area"),
    "wheelchair": (24, "Wheelchair accessible"),
    "parking": (25, "Parking available"),
    "public": (26, "Public transportation"),
    "water": (27, "Drinking water nearby"),
    "restrooms": (28, "Public restrooms nearby"),
    "phone": (29, "Telephone nearby"),
    "picnic": (30, "Picnic tables nearby"),
    "camping": (31, "Camping available"),
    "bicycles": (32, "Bicycles"),
    "motorcycles": (33, "Motorcycles"),
    "quads": (34, "Quads"),
    "jeeps": (35, "Off-road vehicles"),
    "snowmobiles": (36, "Snowmobiles"),
    "horses": (37, "Horses"),
    "campfires": (38, "Campfires"),
    "thorns": (39, "Thorns"),
    "thorn": (39, "Thorns!"),
    "stealth": (40, "Stealth required"),
    "stroller": (41, "Stroller accessible"),
    "firstaid": (42, "Needs maintenance"),
    "cow": (43, "Watch for livestock"),
    "flashlight": (44, "Flashlight required"),
    "landf": (45, "Lost And Found Tour"),
    }

cache_type_map = {
    "2": "traditional",
    "3": "multicache",
    "ape_32": "ape",
    "8": "mystery",
    "5": "letterbox",
    "1858": "whereigo",
    "6": "event",
    "mega": "megaevent",
    "13": "cito",
    "earthcache": "earthcache",
    "1304": "adventuremaze",
    "4": "virtual",
    "11": "webcam",
    "10Years_32": "10years",
    "12":"locationless"
    }

def find_or_create(cache, tag):
    query = cache.xpath('.//*[local-name()="%s"]' % tag)
    if len(query) != 0:
        return query[0]

    groundspeak = cache.nsmap["groundspeak"]
    element = etree.Element("{%s}%s" % (groundspeak, tag))
    cache.append(element)
    return element

def cache_type(code):
    if code in cache_type_map:
        return cache_type_map[code]
    return code.lower().strip().replace(' ', '-')

def lookup_by_header(soup, header):
    for h2 in soup.findAll("h2"):
        if header in h2.text:
            div = h2.findParent().findParent()
            return div.find("div", {"class": "item-content"})

class Geo(object):
    cache_dir = os.path.expanduser("~/.cache/geocaching-py")
    config_dir = os.path.expanduser("~/.config/geocaching-py")
    
    def __init__(self, base_url="http://www.geocaching.com"):
        """
        Initialize GeoCaching.com interface, optionally with a user login and password
        """
        for dirname in (self.cache_dir, self.config_dir):
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
        
        self.cookie_jar = cookielib.MozillaCookieJar(
            os.path.join(self.cache_dir, "cookies.txt"))
        self.cookie_jar.load()
        atexit.register(self.cookie_jar.save)
        self.cookie_processor = urllib2.HTTPCookieProcessor(self.cookie_jar)
        self.opener = urllib2.build_opener(self.cookie_processor)
        self.base_url = base_url

    def page_url(self, rel):
        return urljoin(self.base_url, rel)

    def send(self, url, data=None):
        reqtype = data and "POST" or "GET"
        print >> sys.stderr, "Sending %s request to %s" % (reqtype, url)
        return self.opener.open(url, data).read()
        
    def send_req(self, url, data=None):
        data = self.send(url, data)
        print >> sys.stderr, "Parsing"
        return html.parse(StringIO(data))

    def login_from_config(self):
        login, password = open(os.path.join(self.config_dir, "login")).read().strip().split(':', 1)
        return self.login(login, password)

    def login(self, login, password):
        page = self.page_url("/login/default.aspx")
        et = self.send_req(page)

        username = extract_username(et)
        if username is not None:
            if username == login:
                return username
            self.cookie_jar.clear()
            et = self.send_req(page)

        params = {}
        for input in (et.findall('//input[@type="hidden"]') + 
                      et.findall('//input[@type="submit"]')):
            params[input.name] = input.value
        params[et.find('//input[@type="text"]').name] = login
        params[et.find('//input[@type="password"]').name] = password
        params[et.find('//input[@type="checkbox"]').name] = "1"

        login_url = urljoin(page, et.find('//form').action)
        et = self.send_req(login_url, urlencode(params))
        return extract_username(et)

    def guid_from_gc(self, geocode):
        cache_details_url = self.page_url("/seek/cache_details.aspx?wp=" + geocode)
        et = self.send_req(cache_details_url)

        if not et.find('//title').text.strip().startswith(geocode):
            return None

        print_links = et.xpath('//a[contains(@href, "cdpf.aspx")]')
        if len(print_links) == 0:
            return None
        guid = cgi.parse_qs(urlparse(print_links[0].get("href")).query)["guid"][0]
        return guid
        
    def cache_gpx(self, guid):
        printable_url = self.page_url("/seek/cdpf.aspx?guid=" + guid)
        sendtogps_url = self.page_url("/seek/sendtogps.aspx?guid=" + guid)

        info_plain = self.send(printable_url)
        info = html.parse(StringIO(info_plain))
        print >> sys.stderr, "Parsing printable version with BeautifulSoup"
        info_soup = BeautifulSoup(info_plain)
        
        s2gps = self.send(sendtogps_url)
        s2gps = s2gps[s2gps.index("<?xml"):s2gps.index("</gpx>")+6]
        gpx = etree.parse(StringIO(s2gps))

        cache = tools.cache(gpx)
        if cache is None:
            return None

        short_desc = find_or_create(cache, "short_description")

        long_desc = find_or_create(cache, "long_description")
        hints = find_or_create(cache, "encoded_hints")

        tmp = lookup_by_header(info_soup, "Short Description")
        if tmp is not None:
            short_desc.text = re.sub(r'\s+', ' ', tmp.text.strip())
        else:
            short_desc.text = ""
        tmp = lookup_by_header(info_soup, "Long Description")
        if tmp is not None:
            long_desc.text = tmp.renderContents().decode('utf-8')
        else:
            long_desc.text = ""
        long_desc.set("html", "True")

        try:
            h = lookup_by_header(info_soup, "Additional Hints")
            if h is not None:
                decr = h.find("div", {"class": "hint-encrypted"})
                hints.text = decr.text.strip()
            #hints_text = re.sub(r'\s+', ' ', info_soup.find("div", {"id":"div_hint"}).div.renderContents().decode('utf-8')).strip()
            #hints_text = re.sub(r'<br ?/?>', "\n", hints_text).decode("rot13")
            #hints.text = hints_text
        except AttributeError:
            hints.text = "No hint"

        attrs = find_or_create(cache, "attributes")
        for path in info.xpath('//img[contains(@src, "/attributes/")]/@src'):
            name, yesno = path.split("/")[-1].strip(".gif").split("-")
            if name in attribute_map:
                attr = find_or_create(attrs, "attribute")
                attr.set("id", str(attribute_map[name][0]))
                attr.text = attribute_map[name][1]
                if yesno == "yes":
                    attr.set("inc", "1")
                else:
                    attr.set("inc", "0")
                attrs.append(attr)
                    
        return gpx

    def address_to_coords(self, address):
        """
        Get the coordinates using Google Maps API from the given address
        """
        params = urlencode({"sensor": "false",
                            "address": address})
        url = "http://maps.googleapis.com/maps/api/geocode/json?" + params
        results = json.loads(self.send(url))
        if results['status'] != 'OK':
            return None
        if len(results['results']) > 1:
            print "Warning: search for %s returned more then one results, using the first one" % address
        result = results['results'][0]
        location = result['geometry']['location']
        return "%.7f" % location['lat'], "%.7f" % location['lng']

    def parse_page(self, et):
        query = et.xpath('//table[contains(@class, "SearchResultsTable")]')
        if len(query) == 0:
            print "Results table not found"
            return None
        table = query[0]
        results = []
        rows = table.xpath('./tr[contains(@class, "Data")]')
        for row in rows:
            url = row.xpath('.//img[contains(@src, "wpttypes")]')[0].get("src")
            wpt_type = cache_type(url.split('/')[-1].split('.')[0])
            cols = row.xpath("./td")
            a = cols[5].xpath('.//a')[0]
            p = cgi.parse_qs(urlparse(a.get('href')).query)
            title = a.text_content()
            guid = p['guid'][0]
            geocode = None
            disabled = False
            for p in cols[5].text_content().split():
                if p.startswith("GC"): geocode = p
            if len(row.xpath('.//*[contains(@class, "Strike")]')) > 0:
                disabled = True
            results.append((wpt_type, guid, geocode, disabled, title))

        page_builders = et.xpath('//td[contains(@class, "PageBuilderWidget")]')
        next_url = None
        next_data = {}
        if len(page_builders) == 4:
            builder = page_builders[1]
            for a in builder.xpath('.//a'):
                if 'Next' in a.text_content():
                    href = a.get('href')
                    if href is not None:
                        postback = href.split("'")[1]
                        form = et.find("//form")
                        next_url = form.get("action")
                        for elt in form.xpath('.//input[@type="hidden"]'):
                            if elt.name.startswith("__"):
                                next_data[elt.name] = elt.value
                        next_data['__EVENTTARGET'] = postback
                        next_data['__EVENTARGUMENT'] = ''
                        

        return results, next_url, next_data

    def find_by_address(self, address, radius=100):
        """
        returns a number of caches, number of result pages first result page etree and base url

        radius is in km
        """
        miles = "%.2f" % (float(radius) / 1.609344)

        coords = self.address_to_coords(address)
        if coords is None:
            return None

        params = urlencode({'lat': coords[0],
                            'lng': coords[1],
                            'dist': miles})
        url = self.page_url("/seek/nearest.aspx?"+params)
        et = self.send_req(url)

        total_records = 0
        total_pages = 0
        try:
            b = et.xpath('//*[contains(span, "Total Records")]/span')[0].findall('./b')
            total_records = int(b[0].text)
            total_pages = int(b[2].text)
        except (TypeError, AttributeError), exc:
            print "Error searching total records:", exc
            return None

        print "%d caches on %d pages" % (total_records, total_pages)

        return total_records, total_pages, et, url

    def get_search_results(self, start_et, base_url, count=None):
        """
        Parse and download search results from the results pages,
        but no more then approximately count results (set None for infinity)
        """
        results = []
        et = start_et
        while True:
            part, next_url, next_data = self.parse_page(et)
            results.extend(part)
            if count is not None and len(results) >= count:
                results = results[:count]
                break
            if next_url is not None:
                et = self.send_req(urljoin(base_url, next_url), urlencode(next_data))
            else:
                break

        return results
