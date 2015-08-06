TESTNAME="roof_ridge_strip" #must be one of the valid test-names defined in qc.__init__
TARGS=["-layersql","select wkb_geometry from geodk.bygning where ST_Intersects(wkb_geometry,ST_GeomFromText(WKT_EXT,25832))","-search_factor","1.2","-use_all"]

