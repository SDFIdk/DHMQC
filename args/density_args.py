TESTNAME="density_check" #must be one of the valid test-names defined in qc.__init__
TARGS=["-seasql","select wkb_geometry from hav.hav_tiled where ST_Intersects(wkb_geometry,ST_GeomFromText(WKT_EXT,25832))",
"-lakesql","select wkb_geometry from geodk.soe where ST_Intersects(wkb_geometry,ST_GeomFromText(WKT_EXT,25832))"]




