#####################################################
## Write a simple sqlite-file with tile coverage geometries...  (tifs, las, etc..)##
#####################################################

import sqlite3
import os, sys, re
import argparse
from qc.thatsDEM import dhmqc_constants as constants
#TODO - create a spatialite db . Useful when many tiles...
CREATE_DB="CREATE TABLE coverage(wkt_geometry TEXT, tile_name TEXT unique, path TEXT, mtime INTEGER, row INTEGER, col INTEGER, comment TEXT)"
parser=argparse.ArgumentParser(description="Write a sqlite file readable by e.g. ogr with tile coverage.")
parser.add_argument("path",help="Path to directory to walk into")
parser.add_argument("ext",help="Extension of relevant files")
parser.add_argument("dbout",help="Name of output sqlite file.")
parser.add_argument("-update",action="store_true",help="Update timestamp and/or add new tiles from path.")
parser.add_argument("-append",action="store_true",help="Append to an already existing database.")
parser.add_argument("-exclude",help="Regular expression of subdirs to exclude.")
parser.add_argument("-depth",help="Max depth of subdirs to walk into (defaults to full depth)",type=int)

def main(args):
	pargs=parser.parse_args(args[1:])
	db_name=pargs.dbout
	con=sqlite3.connect(db_name)
	cur=con.cursor()
	if not (pargs.append or pargs.update):
		print("Creating coverage table.")
		cur.execute(CREATE_DB)
	else:
		if pargs.append:
			print("Appending to coverage table.")
		elif pargs.update:
			print("Updating coverage table.")
		cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coverage'")
		tables=cur.fetchone()
		if len(tables)==0:
			raise ValueError("The coverage table does not exist in "+db_name)
	n_insertions=0
	n_updates=0
	n_excluded=0
	badnames=[]
	ext_match=pargs.ext
	walk_path=os.path.realpath(pargs.path)
	if not ext_match.startswith("."):
		ext_match="."+ext_match
	for root, dirs, files in os.walk(walk_path):
		if root==walk_path:
			depth=0
		else:
			depth=len(os.path.relpath(root,walk_path).split(os.path.sep))
		if pargs.depth is not None and pargs.depth<depth:
			continue
		if (pargs.exclude is not None) and (re.search(pargs.exclude,root)):
			n_excluded+=1
			continue
		for name in files:
			ext=os.path.splitext(name)[1]
			if ext==ext_match:
				tile=constants.get_tilename(name)
				path=os.path.join(root,name)
				try:
					wkt=constants.tilename_to_extent(tile,return_wkt=True)
				except:
					badnames.append(path)
				else:
					row,col=constants.tilename_to_index(tile)
					mtime=int(os.path.getmtime(path))
					insert=True
					if pargs.update:
						cur.execute("select mtime from coverage where tile_name=?",(tile,))
						data=cur.fetchone()
						if data is None:
							insert=True
						elif mtime>int(data[0]):
							insert=False
							cur.execute("update coverage set mtime=? where tile_name=?",(mtime,tile))
							con.commit()
							n_updates+=1
						else:
							insert=False
					if insert:	
						cur.execute("insert into coverage (wkt_geometry,tile_name,path,mtime,row,col) values (?,?,?,?,?,?)",(wkt,tile,path,mtime,row,col)) 
						n_insertions+=1
						if n_insertions%200==0:
							print("Done: {0:d}".format(n_insertions))
						con.commit()
			
	cur.close()
	con.close()
	print("Inserted {0:d} rows into {1:s}".format(n_insertions,pargs.dbout))
	print("Updated {0:d} rows".format(n_updates))
	if n_excluded>0:
		print("Excluded {0:d} paths".format(n_excluded))
	if len(badnames)>0:
		print("Encountered {0:d} bad tile-names (first 10..)".format(len(badnames)))
		for name in badnames[:10]:
			print(name)
	return 0

if __name__=="__main__":
	main(sys.argv)