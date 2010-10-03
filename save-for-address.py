#!/usr/bin/python
# -*- encoding: utf-8 -*-

import operator
import optparse
import sys

from geocaching import Geo, tools

def main():
    parser = optparse.OptionParser(usage="%prog radius address...",
                                   description="Download caches for the given address and radius in km")
    opts, args = parser.parse_args()
    if len(args) < 2:
        parser.print_help()
        sys.exit(1)

    radius = int(args[0])
    address = ' '.join(args[1:])
        
    geo = Geo()
    print "Logged in as %s" % geo.login_from_config()
    count, pages, et, url = geo.find_by_address(address)
    print "Found %d caches on %d result pages." % (count, pages)
    print "Please enter the number of caches to download"
    print "(or just hit enter for all):"
    count = raw_input().strip()
    if count == '':
        count = None
    else:
        count = int(count)

    caches = geo.get_search_results(et, url, count)
    print "%-12s|%-8s|%s| %s" % ("Type", "Code", "X", "Title")
    print "------------+--------+-+-----------------------------"
    for cache in caches:
        print "%-12s|%-8s|%s| %s" % (cache[0], cache[2], cache[3] and '-' or '+', cache[4])

    print "Continue to download (only available caches will be downloaded)?"
    yesno = raw_input().strip().lower()
    if yesno[0] != 'y':
        sys.exit(0)

    valid = [cache[1] for cache in caches if not cache[3]]
    for i, guid in enumerate(valid):
        print ">>>>>>>>> Downloading information for cache %d of %d" % (i+1, len(valid))
        gpx = geo.cache_gpx(guid)
        if gpx is None:
            print "Cache %s not found." % arg
            continue
        geocode = tools.geocode(gpx)
        if geocode is None:
            print "Can't parse cache %s, skipping", arg
            continue
        filename = "%s.gpx" % geocode
        gpx.write(open(filename, "w"),
                  encoding="utf-8", xml_declaration=True,
                  pretty_print=True)
        print ">>>>>>>>> Wrote %s" % filename

if __name__ == '__main__':
    main()
