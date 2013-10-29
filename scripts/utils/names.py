################
## Name handling module...
##################
import os
def get_1km_name(name):
	b_name=os.path.splitext(os.path.basename(name))[0]
	i=b_name.find("1km")
	if i!=-1:
		kmname=b_name[i:]  #improve 
	else:
		kmname=b_name
	return kmname

#This function should reflect the directory layout of clipped vector files...
def get_vector_tile(basedir,lasname):
	kmname=get_1km_name(lasname)
	tokens=kmname.split("_")
	if len(tokens)!=3 or tokens[0]!="1km": #something wrong
		raise ValueError("Bad 1km input name: {0}".format(lasname))
	N=int(tokens[1])
	E=int(tokens[2])
	N10=int(N/10)
	E10=int(E/10)
	km10name="10km_{0}_{1}".format(str(N10),str(E10))
	basename=kmname+".shp"
	vector_tile=os.path.join(basedir,km10name,basename)
	return vector_tile
	
	