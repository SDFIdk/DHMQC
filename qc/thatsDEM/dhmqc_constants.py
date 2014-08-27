#This is kind of a 'project' specific constants file

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

#Most of the qc-system is based on an assumption that we have tiled las input files, whose tile-georeference is encoded into the name of a las-file e.g. 1km_nnnn_eee.las
#tile size defined here in meters
tile_size=1000

#Limits for acceptable terrain heights defined here - these limits should reflect whether the project uses ellipsoidal or geophysical heights!!
z_min_terrain=10     #probaly higher....
z_max_terrain=230  #sensible limits for DK??


#TODO: limits for clouds, steep triangles, etc...




