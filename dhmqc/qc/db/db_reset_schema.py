# Copyright (c) 2015-2016, Danish Geodata Agency <gst@gst.dk>
# Copyright (c) 2016, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
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
import os,sys
import psycopg2
from thatsDEM.dhmqc_constants import PG_CONNECTION
#PG_DB= "dbname='dhmqc' user='postgres' host='localhost' password='postgis'"


MyTruncateCmd = """Truncate SKEMANAVN.f_z_precision_roads;
Truncate SKEMANAVN.f_z_precision_buildings; 
Truncate SKEMANAVN.f_z_precision_buildings;
Truncate SKEMANAVN.f_classification;
Truncate SKEMANAVN.f_classes_in_tiles;
Truncate SKEMANAVN.f_roof_ridge_alignment;
Truncate SKEMANAVN.f_roof_ridge_strips;
Truncate SKEMANAVN.f_xy_accuracy_buildings;
Truncate SKEMANAVN.f_z_accuracy;
Truncate SKEMANAVN.f_xy_precision_buildings;
Truncate SKEMANAVN.f_auto_building;
Truncate SKEMANAVN.f_clouds;
"""

MyDeleteCmd = """delete from SKEMANAVN.f_z_precision_roads where run_id=THERUNID;
delete from SKEMANAVN.f_z_precision_buildings where run_id=THERUNID;
delete from SKEMANAVN.f_z_precision_buildings where run_id=THERUNID;
delete from SKEMANAVN.f_classification where run_id=THERUNID;
delete from SKEMANAVN.f_classes_in_tiles where run_id=THERUNID;
delete from SKEMANAVN.f_roof_ridge_alignment where run_id=THERUNID;
delete from SKEMANAVN.f_roof_ridge_strips where run_id=THERUNID;
delete from SKEMANAVN.f_xy_accuracy_buildings where run_id=THERUNID;
delete from SKEMANAVN.f_z_accuracy where run_id=THERUNID;
delete from SKEMANAVN.f_xy_precision_buildings where run_id=THERUNID;
delete from SKEMANAVN.f_auto_building where run_id=THERUNID;
delete from SKEMANAVN.f_clouds where run_id=THERUNID;
"""


def usage():
	print("Usage:\n%s <schema name> -reset | -runid <run id>" %os.path.basename(sys.argv[0]))
	print(" ")
	print("<schema name>          The schema name to either reset or delete from")
	print("-resetall              All data in the schema will be deleted")
	print("-runid <runid>         Only delete a certain run id")
	print("\n")
	print("either -reset OR -runid must be given")
	print("\n")
	print("The database connection (specified in dhmqc_constants.py) will be used:")
	print("         "+PG_CONNECTION)
	sys.exit(1)
  
def main(args):
	runid = ""
	resetall = False
	if len(args)<3:
		usage()
	if "-resetall" in args:
		resetall = True
	else: 
		resetall = False
	
	if "-runid" in args: 
		i=args.index("-runid")
		runid=args[i+1]
	
	if resetall and runid!="":
		print("only one of -resetall and -runid can be given")
		sys.exit(1)
	
	
	PSYCOPGCON = PG_CONNECTION.replace("PG: ","")
	
	MyFancyNewSchema = args[1]
	
	if resetall:
		myNewCmd = MyTruncateCmd.replace('SKEMANAVN',MyFancyNewSchema)
	else:
		myNewCmd = MyDeleteCmd.replace('SKEMANAVN',MyFancyNewSchema).replace('THERUNID',runid)
	
#	print resetall
#	print runid
#	print ("Kommando: "+ myNewCmd)
#	print ("exit'ing")
	
#	sys.exit(1)
	
	conn = psycopg2.connect(PSYCOPGCON)
	cur=conn.cursor()
	cur.execute(myNewCmd)
	conn.commit()	
	cur.close()
	conn.close()

if __name__=="__main__":
	main(sys.argv)
