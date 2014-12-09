#This is kind of a 'project' specific constants file
import os, glob
#According to the project plan (table 4.1, page 43) we will receive following classes: 
created_unused=0
surface=1
terrain=2
low_veg=3
med_veg=4
high_veg=5
building=6
outliers=7
mod_key=8
water=9
ignored=10
bridge=17
man_excl=32

#a list to iterate for more systematic usage - important for reporting that the order here is the same as in the table definition in report.py!!
classes=[0,1,2,3,4,5,6,7,8,9,10,17,32]


#Database connection string (ogr)
PG_CONNECTION= "PG: dbname='dhmqc' user='postgres' host='c1200038' password='postgres'"


#Limits for acceptable terrain heights defined here - these limits should reflect whether the project uses ellipsoidal or geophysical heights!!
z_min_terrain=10     #probaly higher....
z_max_terrain=230  #sensible limits for DK??

#Default spatial reference system
srs="EPSG:25832"


#TODO: limits for clouds, steep triangles, etc...



#Most of the qc-system is based on an assumption that we have tiled las input files, whose tile-georeference is encoded into the name of a las-file e.g. 1km_nnnn_eee.las
#tile size defined here in meters
tile_size=1000

def tilename_to_extent(tilename, return_wkt=False):
	#might throw an exception - wrap in try, except...
	N,E=tilename.split("_")[1:3]
	N=int(N)
	E=int(E)
	xt=(E*tile_size,N*tile_size,(E+1)*tile_size,(N+1)*tile_size)
	if return_wkt:
		wkt="POLYGON(("
		for dx,dy in ((0,0),(0,1),(1,1),(1,0)):
			wkt+="{0:.2f} {1:.2f},".format(xt[2*dx],xt[2*dy+1])
		wkt+="{0:.2f} {1:.2f}))".format(xt[0],xt[1])
		return wkt
	#x1,y1,x2,y2 - fits into the array_geometry.bbox_to_polygon method
	return xt

def point_to_tilename(x,y):
	E=int(x/tile_size)
	N=int(y/tile_size)
	return "1km_{0:d}_{1:d}".format(N,E)

def tilename_to_index(tilename):
	N,E=tilename.split("_")[1:3]
	N=int(N)
	E=int(E)
	return 6200-N,E-600

def get_tilename(name):
	b_name=os.path.splitext(os.path.basename(name))[0]
	i=b_name.find("1km")
	if i!=-1:
		items=b_name[i:].split("_")[:3]
		kmname="_".join(items)
	else:
		kmname=b_name
	return kmname


#This function should reflect the directory layout of clipped vector files...
#now somewhat more flexible... simple_layout=True to use ref-tiles in a single directory...!
def get_vector_tile(basedir,lasname,ext=".shp",simple_layout=False):
	kmname=get_tilename(lasname)
	tokens=kmname.split("_")
	if len(tokens)<3 or (not "1km" in tokens): #something wrong
		raise ValueError("Bad 1km input name: {0}".format(lasname))
	i=tokens.index("1km")
	N=int(tokens[i+1])
	E=int(tokens[i+2])
	if not simple_layout:
		N10=int(N/10)
		E10=int(E/10)
		km10name="*{0:d}_{1:d}".format(N10,E10)
		dirs=glob.glob(os.path.join(basedir,km10name))
		if len(dirs)>0:
			km10name=dirs[0]
		else:
			return None
	else:
		km10name=basedir
	basename="*{0:d}_{1:d}{2:s}".format(N,E,ext)
	pattern=os.path.join(km10name,basename)
	tiles=glob.glob(pattern)
	if len(tiles)>0:
		return tiles[0]
	return None





