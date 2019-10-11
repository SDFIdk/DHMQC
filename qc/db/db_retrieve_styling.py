from __future__ import print_function
from __future__ import absolute_import
# Copyright (c) 2015-2016, Danish Geodata Agency <gst@gst.dk>
# Copyright (c) 2016, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
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
from builtins import str
import os,sys
import psycopg2
try:
    from  .pg_connection import PG_CONNECTION
except Exception as e:
	print("Failed to import pg_connection.py - you need to specify the keyword PG_CONNECTION!")
	print(str(e))
	raise e

def usage():
	print("Usage:\n%s <from schema name> <to schema name>" %os.path.basename(sys.argv[0]))
	print(" ")
	print("<from schema name>          The schema containing styling")
	print("<to schema name>            Schema to store styling")
	sys.exit(1)

def main(args):
	if len(args)<3:
		usage()
		sys.exit(1)
	PSYCOPGCON = PG_CONNECTION.replace("PG:","").strip()
	schema = args[1]
	to_schema = args[2]
	conn = psycopg2.connect(PSYCOPGCON)
	cur=conn.cursor()
	MyCommand = "delete from public.layer_styles where f_table_schema = '%s'" %to_schema
	cur.execute(MyCommand)
	conn.commit()			
	MyCommand = "select f_table_name from public.layer_styles where f_table_schema = '%s'" %schema
	cur.execute(MyCommand)
	conn.commit()	
	cur2=conn.cursor()
	for record in cur:
		print("styling %s" %record)
		MyCommand2 = """INSERT INTO public.layer_styles (f_table_catalog, f_table_name, f_geometry_column, stylename, styleqml, stylesld, useasdefault, description, owner, ui, update_time) select f_table_catalog, f_table_name, f_geometry_column, stylename, styleqml, stylesld, useasdefault, description, owner, ui, update_time from public.layer_styles where f_table_schema = '%s' and f_table_name = '%s' ;""" %(schema, record[0])
		cur2.execute(MyCommand2)
		conn.commit()
	
	MyCommand3 = """update public.layer_styles set f_table_schema = '%s' where f_table_schema is null;""" %(to_schema)
	cur2.execute(MyCommand3)
	conn.commit()
	cur2.close()
	cur.close()
	conn.close()
	sys.exit(1)	
		
if __name__=="__main__":
	main(sys.argv)
