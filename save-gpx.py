#!/usr/bin/python
# -*- encoding: utf-8 -*-

import optparse
import sys

from geocaching import Geo

def main():
    parser = optparse.OptionParser(usage="%prog GC-code [GC-code ...]",
                                   description="Saves GPX data to GCCODE.gpx files")
    opts, args = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        sys.exit(1)
        
    geo = Geo()
    print "Logged in as %s" % geo.login_from_config()
    for gccode in args:
        gpx = geo.cache_gpx(gccode)
        if gpx is None:
            print "Cache %s not found." % gccode
            continue
        gpx.write(open("%s.gpx" % gccode, "w"),
                  encoding="utf-8", xml_declaration=True,
                  pretty_print=True)

if __name__ == '__main__':
    main()
