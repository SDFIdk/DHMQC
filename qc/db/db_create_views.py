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
import os,sys
import psycopg2
try:
	from  pg_connection import PG_CONNECTION
except Exception,e:
	print("Failed to import pg_connection.py - you need to specify the keyword PG_CONNECTION!")
	print(str(e))
	raise e

MyBigSqlCmd=""" 
CREATE OR REPLACE VIEW SKEMANAVN.v_classi_buildpoints as
SELECT
  ogc_fid, km_name, f_building_6, wkb_geometry
FROM 
  SKEMANAVN.f_classification
WHERE
  ((ptype = 'building') and (f_building_6 < 0.4) and (f_high_veg_5<0.5) and (st_area(wkb_geometry)>25) and ((n_points_total/st_area(wkb_geometry)) >2.5) ) ;

CREATE OR REPLACE VIEW SKEMANAVN.v_classi_terrain_in_buildings as
SELECT
  ogc_fid, km_name, f_terrain_2, n_points_total, wkb_geometry
FROM 
  SKEMANAVN.f_classification
WHERE
  ((ptype = 'building') and (st_area(wkb_geometry)>800) and (n_points_total>2000) and (f_terrain_2>0.3));

CREATE OR REPLACE VIEW SKEMANAVN.v_classi_bridgepoints as
SELECT
  ogc_fid, km_name, f_bridge_17, wkb_geometry
FROM 
  SKEMANAVN.f_classification
WHERE
  ((ptype = 'bridge') and (f_bridge_17 < 0.01) ) ;

CREATE OR REPLACE VIEW SKEMANAVN.v_classi_plants_under_building as
SELECT
  ogc_fid, km_name, f_terrain_2, f_low_veg_3, f_med_veg_4, f_high_veg_5, f_building_6, wkb_geometry
FROM 
  SKEMANAVN.f_classification
WHERE
  ( (ptype = 'below_poly') and (n_points_total > 0) and ((f_low_veg_3 >0.10)or( f_med_veg_4>0.10)or(f_high_veg_5>0.03))  ) ;


CREATE OR REPLACE VIEW SKEMANAVN.v_classi_lakepoints as
SELECT
  ogc_fid, km_name, f_water_9, wkb_geometry
FROM 
  SKEMANAVN.f_classification
WHERE
  ((ptype = 'lake') and (f_water_9 < 0.015) ) ;
  
CREATE OR REPLACE VIEW SKEMANAVN.v_tile_z_precision_roads AS 
 SELECT km.ogc_fid, km.wkb_geometry, 
    km.tilename AS tilename, 
    avg(abs(zc.mean12)) AS abs_avg12,
    avg(abs(zc.mean21)) AS abs_avg21,
    avg(sigma12) as sigma12,
    avg(sigma21) as sigma21
   FROM SKEMANAVN.f_z_precision_roads zc, 
    dhmqc.f_dk1km km
  WHERE km.tilename = zc.km_name
  GROUP BY km.ogc_fid, km.tilename, km.wkb_geometry;
  
ALTER VIEW SKEMANAVN.v_tile_z_precision_roads
  OWNER TO postgres;
  
CREATE OR REPLACE VIEW SKEMANAVN.v_tile_z_precision_buildings AS 
 SELECT km.ogc_fid, km.wkb_geometry, 
    km.tilename AS tilename, 
    avg(abs(zc.mean12)) AS abs_avg12,
    avg(abs(zc.mean21)) AS abs_avg21,
    avg(sigma12) as sigma12,
    avg(sigma21) as sigma21
   FROM SKEMANAVN.f_z_precision_buildings zc, 
    dhmqc.f_dk1km km
  WHERE km.tilename = zc.km_name
  GROUP BY km.ogc_fid, km.tilename, km.wkb_geometry;
  
ALTER VIEW SKEMANAVN.v_tile_z_precision_buildings
  OWNER TO postgres;  

create or replace view SKEMANAVN.v_classes_distribution as select 
  ogc_fid, 
  km_name, 
  round(100*n_created_00/n_points_total) as pct_created_00,
  round(100*n_surface_1/n_points_total) as pct_surface_1,
  round(100*n_terrain_2/n_points_total) as pct_terrain_2,
  round(100*n_low_veg_3/n_points_total) as pct_low_veg_3, 
  round(100*n_med_veg_4/n_points_total) as pct_med_veg_4,
  round(100*n_high_veg_5/n_points_total) as pct_high_veg_5,
  round(100*n_building_6/n_points_total) as pct_building_6,
  round(100*n_outliers_7/n_points_total) as pct_outliers_7,
  round(100*n_mod_key_8/n_points_total) as pct_mod_key_8,
  round(100*n_water_9/n_points_total) as pct_water_9,
  round(100*n_ignored_10/n_points_total) as pct_ignored_10,
  round(100*n_bridge_17/n_points_total) as pct_bridge_17,
  round(100*n_man_excl_32/n_points_total) as pct_man_excl_32,
  n_points_total,
  wkb_geometry 
from SKEMANAVN.f_classes_in_tiles
where n_points_total >0;

ALTER VIEW SKEMANAVN.v_classes_distribution
  OWNER TO postgres;  """

def usage():
	print("Usage:\n%s <schema name>" %os.path.basename(sys.argv[0]))
	print(" ")
	print("<schema name>:  ")
	print("         The given schema name, necessary tables etc. for running dhmqc will")
	print("         be created in the database with the DB connection specified in")
	print("         dhmqc_constants.py ,currently: ")
	print("\n")
	print("         "+PG_CONNECTION)
	print("")
	sys.exit(1)


def main(args):
	if len(args)<2:
		usage()
	PSYCOPGCON = PG_CONNECTION.replace("PG:","").strip()
	MyFancyNewSchema = args[1]
	myNewCmd = MyBigSqlCmd.replace('SKEMANAVN',MyFancyNewSchema)
	conn = psycopg2.connect(PSYCOPGCON)
	cur=conn.cursor()
	cur.execute(myNewCmd)
	conn.commit()
	cur.close()
	conn.close()
	

if __name__=="__main__":
	main(sys.argv)