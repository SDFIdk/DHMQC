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