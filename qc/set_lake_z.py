import os,sys
from osgeo import ogr

from thatsDEM import pointcloud,array_geometry, grid
import numpy as np

LAKE_LAYER="lakes"
import sys,os,time
#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry,grid
from db import report
import numpy as np
#import pyspatialite.dbapi2 as db
import psycopg2 as db
import dhmqc_constants as constants
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
GEOID_GRID=os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b_utm32.tif")
cut_to=[constants.terrain,constants.water]
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Set lake heights from pointcloud data.",prog=progname)
parser.add_argument("-nowarp",action="store_true",help="Do not warp. Input pointcloud is in output height system (dvr90)")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("db_connection",help="input reference data connection string (e.g to a db, or just a path to a shapefile).")
parser.add_argument("tablename",help="input name of lake layer.")
parser.add_argument("-geometry_column",dest="GEOMETRY_",help="name of geometry column name",default="wkb_geometry")
parser.add_argument("-id_attr",dest="IDATTR_",help="name of unique id attribute.",default="ogc_fid")
parser.add_argument("-burn_z_attr",dest="BURN_Z_",help="name of burn_z attribute.",default="burn_z")
parser.add_argument("-n_used_attr",dest="N_USED_",help="name of n_used attribute",default="n_used")
parser.add_argument("-is_invalid_attr",dest="IS_INVALID_",help="name of is_valid attribute",default="is_invalid")
parser.add_argument("-reason_attr",dest="REASON_",help="name of reason for invalidity / comment attr.",default="reason")
parser.add_argument("-dryrun",action="store_true",help="Simply show sql commands... nothing else...")
parser.add_argument("-reset",action="store_true",help="Reset atttr. Can only be done as __main__")

SQL_SELECT="select ST_AsText(GEOMETRY_),IDATTR_,BURN_Z_,N_USED_ from TABLENAME_ where ST_Area(GEOMETRY_)>16 and ST_Intersects(GEOMETRY_,ST_GeomFromText('WKT_',25832)) and (IS_INVALID_ is null or IS_INVALID_<1)"
SQL_SET_INVALID="update TABLENAME_ set IS_INVALID_=1,REASON_=%s where IDATTR_=%s"
SQL_UPDATE="update TABLENAME_ set IS_INVALID_=0,BURN_Z_=%s,N_USED_=%s where IDATTR_=%s"
SQL_RESET="update TABLENAME_ set BURN_Z_=null,IS_INVALID_=0,N_USED_=0"
SQL_COMMANDS={"select":SQL_SELECT,"set_invalid":SQL_SET_INVALID,"update":SQL_UPDATE,"reset":SQL_RESET}


def set_sql_commands(pargs,wkt):
	out={}
	for key in SQL_COMMANDS:
		sql=SQL_COMMANDS[key]
		sql=sql.replace("TABLENAME_",pargs.tablename)
		sql=sql.replace("WKT_",wkt)
		for attr in ["GEOMETRY_","IDATTR_","BURN_Z_","N_USED_","IS_INVALID_","REASON_"]:
			sql=sql.replace(attr,pargs.__dict__[attr])
		out[key]=sql
	return out
			

def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception,e:
		print(str(e))
		return 1
	kmname=constants.get_tilename(pargs.las_file)
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	tilewkt=constants.tilename_to_extent(kmname,return_wkt=True)
	if not pargs.nowarp:
		geoid=grid.fromGDAL(GEOID_GRID,upcast=True)
	
	sql_commands=set_sql_commands(pargs,tilewkt)
	if pargs.dryrun:
		for key in sql_commands:
			print(key+": "+sql_commands[key])
		return
	con=db.connect(pargs.db_connection)
	cur=con.cursor()
	if pargs.reset:
		if __name__!="__main__":
			raise ValueError("Reset can only be performed as __main__!")
			
		cur.execute(sql_commands["reset"])
		con.commit()
		return
		#hmmm - should crate an index also...
	
	pc=None
	#select all lakes that intersect this tile and for which the burn h is not set,,,
	print(sql_commands["select"])
	t1=time.clock()
	cur.execute(sql_commands["select"])
	lakes=cur.fetchall()
	t2=time.clock()
	print("Found %d lakes in %.3f s" %(len(lakes),t2-t1))
	tg=ogr.CreateGeometryFromWkt(tilewkt)
	for lake in lakes:
		ogc_fid,burn_z,n_used=lake[1:]
		lake_geom=ogr.CreateGeometryFromWkt(lake[0])
		lake_area=lake_geom.GetArea()
		lake_centroid=lake_geom.Centroid()
		lake_centroid_pts=np.asarray(lake_centroid.GetPoints())
		if not pargs.nowarp:
			geoid_h=geoid.interpolate(lake_centroid_pts)[0]
			print("Geoid h is: %.2f" %geoid_h)
		else:
			geoid_h=0
		lake_buf=lake_geom.Buffer(0.4)
		lake_in_tile=lake_geom.Intersection(tg)
		intersection_area=lake_in_tile.GetArea()
		#if intersection_area/lake_area<0.15:
		#	print("Not enough area covered by tile. Dont wanna make any judgements based on that!")
		#	continue
		lake_buffer_in_tile=lake_buf.Intersection(tg)
		print lake_buffer_in_tile.GetGeometryName()
		print lake_buffer_in_tile.GetGeometryCount()
		if pc is None:
			pc=pointcloud.fromLAS(pargs.las_file).cut_to_class(cut_to)
		print "updating where ogc_fid="+str(ogc_fid)
		gtype=lake_buffer_in_tile.GetGeometryType()
		if gtype==ogr.wkbMultiPolygon or gtype==ogr.wkbMultiPolygon25D:
			polys=[lake_buffer_in_tile.GetGeometryRef(i).Clone() for i in range(lake_buffer_in_tile.GetGeometryCount())]
		else:
			polys=[lake_buffer_in_tile]
		arr=array_geometry.ogrpoly2array(polys[0],flatten=True)
		pc_=pc.cut_to_polygon(arr)
		if len(polys)>1:
			print("More than one geometry...")
			for poly in polys[1:]:
				arr=array_geometry.ogrpoly2array(poly,flatten=True)
				pc_.extend(pc.cut_to_polygon(arr))
		print("Size of buffer pc: %d" %pc_.get_size())
		n_used_here=pc_.get_size()
		if n_used_here<200:
			print("Too few points!...")
			continue
		if not pargs.nowarp:
			pc_.z-=geoid_h
		z_dvr90=np.percentile(pc_.z,12.5)
		print ("z dvr90: %.2f" %z_dvr90)
		#validity tests
		is_valid=True
		reason=""
		if n_used>0: 
			dz=abs(burn_z-z_dvr90)
			if dz>0.2: 
				if n_used_here/float(n_used)>0.20 or n_used_here>1000:
					print("Hmm - seeem to be invalid due to large z deviation : %.2f" %dz)
					is_valid=False
				else:
					print("Hmm - deviation to already set is large: %.2f, but not many pts here, continuing." %dz) 
					continue
			reason="deviation to other: %.2f" %dz
		if is_valid and n_used_here>150:
			z2=np.median(pc_.z)
			dz=(z2-z_dvr90)
			if dz>0.2:
				is_valid=False
				reason="internal deviation: %.2f" %dz
		if not is_valid:
			print("Deeemed invalid: "+reason)
			cur.execute(sql_commands["set_invalid"],(reason,ogc_fid))
			con.commit()
			continue
		if n_used>0:
			burn_z=((n_used)*burn_z+(z_dvr90)*n_used_here)/(n_used_here+n_used)
			n_used+=n_used_here
		else:
			burn_z=z_dvr90
			n_used=n_used_here
		cur.execute(sql_commands["update"],(burn_z,n_used,ogc_fid))
		con.commit()
	return 0

if __name__=="__main__":
	main(sys.argv)
		