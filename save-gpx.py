#!/usr/bin/python
# -*- encoding: utf-8 -*-

import optparse
import sys

from geocaching import Geo, tools

def main():
    parser = optparse.OptionParser(usage="%prog GC-code [GC-code ...]",
                                   description="Saves GPX data to GCCODE.gpx files")
    opts, args = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        sys.exit(1)
        
    geo = Geo()
    print "Logged in as %s" % geo.login_from_config()
    for arg in args:
        guid = arg
        if arg.count('-') != 4:
            guid = geo.guid_from_gc(arg)
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
