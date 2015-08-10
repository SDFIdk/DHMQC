TESTNAME="z_precision_roads" #must be one of the valid test-names defined in qc.__init__
TARGS=["-layersql","select wkb_geometry from geodk.vejmidte_brudt where ST_Intersects(wkb_geometry,ST_GeomFromText(WKT_EXT,25832))"]
