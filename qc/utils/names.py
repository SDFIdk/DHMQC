################
## Name handling module...
##################
import os
import glob
def get_1km_name(name):
	b_name=os.path.splitext(os.path.basename(name))[0]
	i=b_name.find("1km")
	if i!=-1:
		kmname=b_name[i:]  #improve 
	else:
		kmname=b_name
	return kmname


#This function should reflect the directory layout of clipped vector files...
#now somewhat more flexible... simple_layout=True to use ref-tiles in a single directory...!
def get_vector_tile(basedir,lasname,ext=".shp",simple_layout=False):
	kmname=get_1km_name(lasname)
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
	
	