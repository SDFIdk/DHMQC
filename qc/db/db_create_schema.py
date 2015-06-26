# Copyright (c) 2015, Danish Geodata Agency <gst@gst.dk>
# 
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
import os,sys
import argparse 
import psycopg2
import report
import db_retrieve_styling
import db_create_views

parser=argparse.ArgumentParser(description="Create PostGis layers and if needed some views.")
parser.add_argument("schema",help="The name of the schema to create.")
parser.add_argument("-style",help="The name of the schema from which to copy styling.")
parser.add_argument("-create_views",action="store_true",help="Create some usefull views on the schema (use db_create_views to create ALL views).")


  
def main(args):
    pargs=parser.parse_args(args[1:])
    l_defined=report.schema_exists(pargs.schema)
    if l_defined:
        print("Nothing to create, schema and all layers already exists!")
    else:
        report.create_schema(pargs.schema)
    if pargs.create_views:
        print("Creating or replacing views.")
        db_create_views.main(['',pargs.schema])	
    if pargs.style is not None:
        arglist=['',pargs.style,pargs.schema]
        db_retrieve_styling.main(arglist)

if __name__=="__main__":
    main(sys.argv)