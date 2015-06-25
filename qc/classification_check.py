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
###########################
## beginnings of building classification check
#########################
import sys,os,time
import dhmqc_constants as constants
import numpy as np
from thatsDEM import pointcloud,vector_io,array_geometry,grid
from db import report
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
#Sensible z-limits for detecting when a 3d-feature seems to be OK. Used in below_poly - note: Ellipsoidal heights
SENSIBLE_Z_MIN=constants.z_min_terrain
SENSIBLE_Z_MAX=constants.z_max_terrain+35
#path to geoid 
GEOID_GRID=os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b.utm32")
DEBUG="-debug" in sys.argv
progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Generate class statistics for input polygons.",prog=progname)
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")
#add some arguments below
parser.add_argument("-type",choices=['building', 'lake', 'bridge'],help="Specify the type of polygon, e.g. building, lake, bridge - used to generate views.")
parser.add_argument("-below_poly",action="store_true",help="Restrict to points which lie below the mean z of the input polygon(s).")
parser.add_argument("-toE",action="store_true",help="Warp the polygon from dvr90 to ellipsoidal heights. Only makes sense if -below_poly is used.")
group = parser.add_mutually_exclusive_group()
group.add_argument("-layername",help="Specify layername (e.g. for reference data in a database)")
group.add_argument("-layersql",help="Specify sql-statement for layer selection (e.g. for reference data in a database)")
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("ref_data",help="input reference data connection string (e.g to a db, or just a path to a shapefile).")


def usage():
	parser.print_help()
	

def main(args):
	try:
		pargs=parser.parse_args(args[1:])
	except Exception,e:
		print(str(e))
		return 1
	kmname=constants.get_tilename(pargs.las_file)
	print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
	if pargs.below_poly:
		below_poly=True
		ptype="below_poly"
	else:
		below_poly=False
		if pargs.type is not None:
			ptype=pargs.type
		else:
			ptype="undefined"
	if below_poly:
		print("Only using points which lie below polygon mean z!")
	pc=pointcloud.fromAny(pargs.las_file)
	print("Classes in pointcloud: %s" %pc.get_classes())
	try:
		extent=np.asarray(constants.tilename_to_extent(kmname))
	except Exception,e:
		print("Could not get extent from tilename.")
		extent=None
	polygons=vector_io.get_geometries(pargs.ref_data,pargs.layername,pargs.layersql,extent)
	nf=0
	use_local=pargs.use_local
	if pargs.schema is not None:
		report.set_schema(pargs.schema)
	reporter=report.ReportClassCheck(use_local) #ds_report=report.get_output_datasource(use_local)
	for polygon in polygons:
		if below_poly:
			if polygon.GetCoordinateDimension()<3:
				print("Error: polygon not 3D - below_poly does not make sense!")
				continue
			a_polygon3d=array_geometry.ogrpoly2array(polygon,flatten=False)[0]
			#warping loop here....
			if (pargs.toE):
				geoid=grid.fromGDAL(GEOID_GRID,upcast=True)
				print("Using geoid from %s to warp to ellipsoidal heights." %GEOID_GRID)
				toE=geoid.interpolate(a_polygon3d[:,:2].copy())
				M=(toE==geoid.nd_val)
				if M.any():
					raise Warning("Warping to ellipsoidal heights produced no-data values!")
				a_polygon3d[:,2]+=toE
			mean_z=a_polygon3d[:,2].mean()
			if mean_z<SENSIBLE_Z_MIN or mean_z>SENSIBLE_Z_MAX:
				print("Warning: This feature seems to have unrealistic mean z value: {0:.2f} m".format(mean_z))
				continue
			del a_polygon3d
		else:
			mean_z=-1
		polygon.FlattenTo2D()
		nf+=1
		ml="-"*70
		print("%s\nFeature %d\n%s" %(ml,nf,ml))
		a_polygon=array_geometry.ogrpoly2array(polygon)
		pc_in_poly=pc.cut_to_polygon(a_polygon)
		if below_poly:
			pc_in_poly=pc_in_poly.cut_to_z_interval(-999,mean_z)
		n_all=pc_in_poly.get_size()
		freqs=[0]*(len(constants.classes)+1)  #list of frequencies...
		if n_all>0:
			c_all=pc_in_poly.get_classes()
			if below_poly and DEBUG:
				print("Mean z of polygon is:        %.2f m" %mean_z)
				print("Mean z of points below is:   %.2f m" %pc_in_poly.z.mean())
			print("Number of points in polygon:  %d" %n_all)
			print("Classes in polygon:           %s" %(str(c_all)))
			#important for reporting that the order here is the same as in the table definition in report.py!!
			n_found=0
			for i,c in enumerate(constants.classes):
				if c in c_all:
					pcc=pc_in_poly.cut_to_class(c)
					n_c=pcc.get_size()
					f_c=n_c/float(n_all)
					n_found+=n_c
					print("Class %d::" %c)
					print("   #Points:  %d" %n_c)
					print("   Fraction: %.3f" % f_c)
					freqs[i]=f_c
			f_other=(n_all-n_found)/float(n_all)
			freqs[-1]=f_other
		send_args=[kmname]+freqs+[n_all,ptype]
		reporter.report(*send_args,ogr_geom=polygon)
		
			
		


	

if __name__=="__main__":
	main(sys.argv)
	