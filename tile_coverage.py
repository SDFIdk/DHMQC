#####################################################
## Write a simple sqlite-file with tile coverage geometries...  (tifs, las, etc..)##
#####################################################

import sqlite3
import os, sys, re
import argparse
from qc.thatsDEM import dhmqc_constants as constants
#TODO - create a spatialite db . Useful when many tiles...
CREATE_DB="CREATE TABLE coverage(wkt_geometry TEXT, tile_name TEXT unique, path TEXT, mtime INTEGER, row INTEGER, col INTEGER, comment TEXT)"
parser=argparse.ArgumentParser(description="Write/modify a sqlite file readable by e.g. ogr with tile coverage.")
subparsers = parser.add_subparsers(help="sub-command help",dest="mode")
parser_create = subparsers.add_parser('create', help='create help', description="create a new database")
parser_create.add_argument("path",help="Path to directory to walk into")
parser_create.add_argument("ext",help="Extension of relevant files")
parser_create.add_argument("dbout",help="Name of output sqlite file.")
parser_create.add_argument("--append",action="store_true",help="Append to an already existing database.")
parser_create.add_argument("--exclude",help="Regular expression of subdirs to exclude.")
parser_create.add_argument("--depth",help="Max depth of subdirs to walk into (defaults to full depth)",type=int)
parser_update=subparsers.add_parser("update",help="Update timestamp of tiles.",description="Update timestamp of existing tiles.")
parser_update.add_argument("dbout",help="Path to existing database")



def connect_db(db_name,must_exist=False):
	try:
		con=sqlite3.connect(db_name)
		cur=con.cursor()
	except Exception,e:
		print("Unable to connect to "+db_name)
		print(str(e))
		raise ValueError("Invalid sqlite db.")
	cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coverage'")
	tables=cur.fetchone()
	exists=tables is not None and (len(tables)==1)
	if must_exist: 
		if not exists:
			raise ValueError("The coverage table does not exist in "+db_name)
	else:
		if exists:
			raise ValueError("The coverage table is already created in "+db_name)
	return con,cur
	
def update_db(con,cur):
	n_updates=0
	n_non_existing=0
	n_done=0
	cur.execute("select rowid,path,mtime from coverage")
	data=cur.fetchall() #move all to memory - speedier an easier, change behaviour for huge databases...
	for row in data:
		id=int(row[0])
		path=row[1]
		mtime=int(row[2])
		if not os.path.exists(path):
			n_non_existing+=1
			continue
		mtime_real=int(os.path.getmtime(path))
		if mtime_real>mtime: #does this make sense, updating the existing iteration?
			cur.execute("update coverage set mtime=? where rowid=?",(mtime,id))
			con.commit()
			n_updates+=1
		n_done+=1
		if n_done%500==0:
			print("Done: {0:d}".format(n_done))
	print("Updated {0:d} rows.".format(n_updates))
	print("Encountered {0:d} non existing paths.".format(n_non_existing))
		

def append_tiles(con,cur,walk_path,ext_match,wdepth=None,rexclude=None):
	n_insertions=0
	n_excluded=0
	n_badnames=0
	n_dublets=0
	for root, dirs, files in os.walk(walk_path):
		if root==walk_path:
			depth=0
		else:
			depth=len(os.path.relpath(root,walk_path).split(os.path.sep))
		if wdepth is not None and wdepth<depth:
			continue
		if (rexclude is not None) and (re.search(rexclude,root)):
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
					n_badnames+=1
				else:
					row,col=constants.tilename_to_index(tile)
					mtime=int(os.path.getmtime(path))
					try:
						cur.execute("insert into coverage (wkt_geometry,tile_name,path,mtime,row,col) values (?,?,?,?,?,?)",(wkt,tile,path,mtime,row,col))
					except: #todo - only escape the proper exception here... sqlite3 Uniqe stuff
						n_dublets+=1
					else:
						n_insertions+=1
						if n_insertions%200==0:
							print("Done: {0:d}".format(n_insertions))
						con.commit()
	print("Inserted {0:d} rows".format(n_insertions))
	print("Encountered {0:d} 'dublet' tilenames".format(n_dublets))
	if n_excluded>0:
		print("Excluded {0:d} paths".format(n_excluded))
	print("Encountered {0:d} bad tile-names.".format(n_badnames))
		
		

def main(args):
	pargs=parser.parse_args(args[1:])
	if pargs.mode=="create":
		db_name=pargs.dbout
		if not pargs.append:
			print("Creating coverage table.")
			con,cur=connect_db(db_name,False)
			cur.execute(CREATE_DB)
		else:
			con,cur=connect_db(db_name,True)
			print("Appending to coverage table.")
		
	else:
		db_name=pargs.dbout
		print("Updating coverage table.")
		con,cur=connect_db(db_name,True)
	if pargs.mode=="create":
		ext_match=pargs.ext
		walk_path=os.path.realpath(pargs.path)
		if not ext_match.startswith("."):
			ext_match="."+ext_match
		append_tiles(con,cur,walk_path,ext_match,pargs.depth,pargs.exclude)
	else:
		update_db(con,cur)
	
	cur.close()
	con.close()
	return 0

if __name__=="__main__":
	main(sys.argv)