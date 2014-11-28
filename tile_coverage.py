#####################################################
## Write a simple sqlite-file with tile coverage geometries...  (tifs, las, etc..)##
#####################################################

import sqlite3
import os, sys, glob
import argparse
from qc.thatsDEM import dhmqc_constants as constants
CREATE_DB="CREATE TABLE coverage(id INTEGER PRIMARY KEY, wkt_geometry TEXT, tile_name TEXT, path TEXT)"
parser=argparse.ArgumentParser(description="Write a sqlite file readable by e.g. ogr with tile coverage.")
parser.add_argument("files",help="Glob pattern matching tiles, e.g. <path>/*.tif")
parser.add_argument("dbout",help="Name of output sqlite file.")

def main(args):
	pargs=parser.parse_args(args[1:])
	files=glob.glob(pargs.files)
	db_name=pargs.dbout
	con=sqlite3.connect(db_name)
	cur=con.cursor()
	cur.execute(CREATE_DB)
	id=0
	for name in files:
		tile=constants.get_tilename(name)
		wkt=constants.tilename_to_extent(tile,return_wkt=True)
		cur.execute("insert into coverage (id,wkt_geometry,tile_name, path) values (?,?,?,?)",(id,wkt,tile,name)) 
		id+=1
	con.commit()
	cur.close()
	con.close()
	return 0

if __name__=="__main__":
	main(sys.argv)