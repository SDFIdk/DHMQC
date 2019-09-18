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
'''
# Result storing module
# Uses ogr simple feature model to store results in e.g. a database
'''
from __future__ import print_function

from __future__ import absolute_import
import os
import datetime

from osgeo import ogr, osr, gdal

try:
    from .pg_connection import PG_CONNECTION
except ImportError:
    PG_CONNECTION = None

if PG_CONNECTION is not None and not PG_CONNECTION.startswith("PG:"):
    PG_CONNECTION = "PG: " + PG_CONNECTION

EPSG_CODE = 25832
USE_LOCAL = False  # global flag which can override parameter in call to get_output_datasource
# we can keep a reference to an open datasource here - can be set pr. process with set_datasource
DATA_SOURCE = None
FALL_BACK = "./dhmqc.sqlite"  # hmm - we should use some kind of fall-back ds, e.g. if we're offline
FALL_BACK_FRMT = "SQLITE"

# Some standard distros do not come with spatialite - so if we wanna use that, set a
if "DHMQC_USE_SPATIALITE" in os.environ and os.environ["DHMQC_USE_SPATIALITE"] == "YES":
    FALL_BACK_DSCO = ["SPATIALITE=YES"]
else:
    FALL_BACK_DSCO = []

# The default schema - default table names should start with this... will
# be replaced if SCHEMA is not None

RUN_ID = None   # A global id, which can be set from a wrapper script pr. process
SCHEMA_NAME = None

# defining a special string type that let's you have longer strings without
# breaking the existing architecture. Not exactly pretty, but it works.
# Most strings in DHMQC fits in 32 bytes, but in certain cases that is not
# enough. That's when you use ogrOFTLongString (256 bytes)
ogrOFTLongString = 1000

def set_run_id(run_id):
    '''Set global run id. Seems to be unused.'''
    global RUN_ID
    if run_id is not None:
        run_id = int(run_id)
    RUN_ID = run_id  # we can also set run_id to None


def set_schema(name):
    '''Set DB schema name'''
    global SCHEMA_NAME
    SCHEMA_NAME = name


class LayerDefinition(object):
    '''Generic layer definition class.'''

    def __init__(self, name, geometry_type, field_list):
        self.name = name
        self.geometry_type = geometry_type
        self.field_list = field_list


# LAYER_DEFINITIONS
# DETERMINES THE ORDERING AND THE TYPE OF THE ARGUMENTS TO THE report METHOD !!!!
LAYERS = {
    "Z_CHECK_ROAD": LayerDefinition(
        "f_z_precision_roads", ogr.wkbLineString25D,
        (("km_name", ogr.OFTString),
         ("id1", ogr.OFTInteger),
         ("id2", ogr.OFTInteger),
         ("mean12", ogr.OFTReal),
         ("mean21", ogr.OFTReal),
         ("sigma12", ogr.OFTReal),
         ("sigma21", ogr.OFTReal),
         ("rms12", ogr.OFTReal),
         ("rms21", ogr.OFTReal),
         ("npoints12", ogr.OFTInteger),
         ("npoints21", ogr.OFTInteger),
         ("combined_precision", ogr.OFTReal),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "Z_CHECK_BUILD": LayerDefinition(
        "f_z_precision_buildings", ogr.wkbPolygon25D,
        (("km_name", ogr.OFTString),
         ("id1", ogr.OFTInteger),
         ("id2", ogr.OFTInteger),
         ("mean12", ogr.OFTReal),
         ("mean21", ogr.OFTReal),
         ("sigma12", ogr.OFTReal),
         ("sigma21", ogr.OFTReal),
         ("rms12", ogr.OFTReal),
         ("rms21", ogr.OFTReal),
         ("npoints12", ogr.OFTInteger),
         ("npoints21", ogr.OFTInteger),
         ("combined_precision", ogr.OFTReal),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "Z_CHECK_ABS": LayerDefinition(
        "f_z_accuracy", ogr.wkbPoint25D,
        (("km_name", ogr.OFTString),
         ("id", ogr.OFTInteger), ("f_type", ogr.OFTString),
         ("mean", ogr.OFTReal),
         ("sigma", ogr.OFTReal),
         ("npoints", ogr.OFTInteger),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "Z_CHECK_GCP": LayerDefinition(
        "f_z_accuracy_gcp", ogr.wkbPoint25D,
        (("km_name", ogr.OFTString),
         ("z", ogr.OFTReal),
         ("dz", ogr.OFTReal),
         ("t_angle", ogr.OFTReal),
         ("t_size", ogr.OFTReal),
         ("run_id", ogr.OFTInteger)
        )
    ),

    "Z_LINE_OUTLIERS": LayerDefinition(
        "f_z_3dline_outliers", ogr.wkbPoint25D,
        (("km_name", ogr.OFTString),
         ("line_id", ogr.OFTString),
         ("z_line", ogr.OFTReal),
         ("dz", ogr.OFTReal),
         ("tolerance", ogr.OFTReal),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "DENSITY": LayerDefinition(
        "f_point_density", ogr.wkbPolygon,
        (("km_name", ogr.OFTString),
         ("min_point_density", ogr.OFTReal),
         ("mean_point_density", ogr.OFTReal),
         ("cell_size", ogr.OFTReal),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    # the ordering of classes here should be numeric as in dhmqc_constants - to not mix up classes!
    "CLASS_CHECK": LayerDefinition(
        "f_classification", ogr.wkbPolygon,
        (("km_name", ogr.OFTString),
         ("f_created_00", ogr.OFTReal),
         ("f_surface_1", ogr.OFTReal),
         ("f_terrain_2", ogr.OFTReal),
         ("f_low_veg_3", ogr.OFTReal),
         ("f_med_veg_4", ogr.OFTReal),
         ("f_high_veg_5", ogr.OFTReal),
         ("f_building_6", ogr.OFTReal),
         ("f_outliers_7", ogr.OFTReal),
         ("f_mod_key_8", ogr.OFTReal),
         ("f_water_9", ogr.OFTReal),
         ("f_ignored_10", ogr.OFTReal),
         ("f_bridge_17", ogr.OFTReal),
         ("f_man_excl_32", ogr.OFTReal),
         ("f_other", ogr.OFTReal),
         ("n_points_total", ogr.OFTInteger),
         ("ptype", ogr.OFTString),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "CLASS_COUNT": LayerDefinition(
        "f_classes_in_tiles", ogr.wkbPolygon,
        (("km_name", ogr.OFTString),
         ("n_created_00", ogr.OFTInteger),
         ("n_surface_1", ogr.OFTInteger),
         ("n_terrain_2", ogr.OFTInteger),
         ("n_low_veg_3", ogr.OFTInteger),
         ("n_med_veg_4", ogr.OFTInteger),
         ("n_high_veg_5", ogr.OFTInteger),
         ("n_building_6", ogr.OFTInteger),
         ("n_outliers_7", ogr.OFTInteger),
         ("n_mod_key_8", ogr.OFTInteger),
         ("n_water_9", ogr.OFTInteger),
         ("n_ignored_10", ogr.OFTInteger),
         ("n_power_line_14", ogr.OFTInteger),
         ("n_bridge_17", ogr.OFTInteger),
         ("n_high_noise_18", ogr.OFTInteger),
         ("n_terr_in_build_19", ogr.OFTInteger),
         ("n_low_veg_in_buld_20", ogr.OFTInteger),
         ("n_man_excl_32", ogr.OFTInteger),

         ("n_points_total", ogr.OFTInteger),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "ROOFRIDGE_ALIGNMENT": LayerDefinition(
        "f_roof_ridge_alignment", ogr.wkbLineString25D,
        (("km_name", ogr.OFTString),
         ("rotation", ogr.OFTReal),
         ("dist1", ogr.OFTReal),
         ("dist2", ogr.OFTReal),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "ROOFRIDGE_STRIPS": LayerDefinition(
        "f_roof_ridge_strips", ogr.wkbLineString25D,
        (("km_name", ogr.OFTString),
         ("id1", ogr.OFTString),
         ("id2", ogr.OFTString),
         ("stripids", ogr.OFTString),
         ("pair_dist", ogr.OFTReal),
         ("pair_rot", ogr.OFTReal),
         ("z", ogr.OFTReal),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "BUILDING_ABSPOS": LayerDefinition(
        "f_xy_accuracy_buildings", ogr.wkbPolygon25D,
        (("km_name", ogr.OFTString),
         ("scale", ogr.OFTReal),
         ("dx", ogr.OFTReal),
         ("dy", ogr.OFTReal),
         ("n_points", ogr.OFTInteger),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "BUILDING_RELPOS": LayerDefinition(
        "f_xy_precision_buildings", ogr.wkbPolygon25D,
        (("km_name", ogr.OFTString),
         ("id1", ogr.OFTString),
         ("id2", ogr.OFTString),
         ("dx", ogr.OFTReal),
         ("dy", ogr.OFTReal),
         ("dist", ogr.OFTReal),
         ("h_scale", ogr.OFTReal),
         ("h_dx", ogr.OFTReal),
         ("h_dy", ogr.OFTReal),
         ("h_sdx", ogr.OFTReal),
         ("h_sdy", ogr.OFTReal),
         ("n_points", ogr.OFTInteger),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "AUTO_BUILDING": LayerDefinition(
        "f_auto_building", ogr.wkbPolygon,
        (("km_name", ogr.OFTString),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "CLOUDS": LayerDefinition(
        "f_clouds", ogr.wkbPolygon,
        (("km_name", ogr.OFTString),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),


    "DELTA_ROADS": LayerDefinition(
        "f_delta_roads", ogr.wkbMultiPoint,
        (("km_name", ogr.OFTString),
         ("z_step_max", ogr.OFTReal),
         ("z_step_min", ogr.OFTReal),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "SPIKES": LayerDefinition(
        "f_spikes", ogr.wkbPoint,
        (("km_name", ogr.OFTString),
         ("filter_rad", ogr.OFTReal),
         ("mean_dz", ogr.OFTReal),
         ("x", ogr.OFTReal),
         ("y", ogr.OFTReal),
         ("z", ogr.OFTReal),
         ("c", ogr.OFTInteger),
         ("pid", ogr.OFTInteger),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "STEEP_TRIANGLES": LayerDefinition(
        "f_steep_triangles", ogr.wkbPoint,
        (("km_name", ogr.OFTString),
         ("class", ogr.OFTInteger),
         ("slope", ogr.OFTReal),
         ("xybox", ogr.OFTReal),
         ("zbox", ogr.OFTReal),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "HOLES": LayerDefinition(
        "f_fill_holes", ogr.wkbPolygon,
        (("km_name", ogr.OFTString),
         ("z1", ogr.OFTReal),
         ("z2", ogr.OFTReal),
         ("dz", ogr.OFTReal),
         ("sd", ogr.OFTReal),
         ("n_old", ogr.OFTInteger),
         ("area", ogr.OFTReal),
         ("dump_name", ogr.OFTString),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime),
         ("accepted", ogr.OFTInteger),
         ("comment", ogr.OFTString)
        )
    ),

    "HOLE_POINTS": LayerDefinition(
        "f_hole_points", ogr.wkbMultiPoint,
        (("km_name", ogr.OFTString),
         ("z1", ogr.OFTReal),
         ("z2", ogr.OFTReal),
         ("dz", ogr.OFTReal),
         ("n_old", ogr.OFTInteger),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),


    "WOBBLY_WATER": LayerDefinition(
        "f_wobbly_water", ogr.wkbPolygon,
        (("km_name", ogr.OFTString),
         ("class", ogr.OFTInteger),
         ("frad", ogr.OFTReal),
         ("npoints", ogr.OFTInteger),
         ("min_diff", ogr.OFTReal),
         ("max_diff", ogr.OFTReal),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "POLY_Z_STATS": LayerDefinition(
        "f_poly_z_stats", ogr.wkbPolygon,
        (("km_name", ogr.OFTString),
         ("class", ogr.OFTInteger),
         ("npoints", ogr.OFTInteger),
         ("zmin", ogr.OFTReal),
         ("zmax", ogr.OFTReal),
         ("zmean", ogr.OFTReal),
         ("sd", ogr.OFTReal),
         ("f5", ogr.OFTReal),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime)
        )
    ),

    "TIME_STATS": LayerDefinition(
        "f_time_stats", ogr.wkbPolygon,
        (("km_name", ogr.OFTString),
         ("min_time", ogr.OFTString),
         ("max_time", ogr.OFTString),
         ("unique_days", ogrOFTLongString),
         ("n_unique_days", ogr.OFTInteger),
         ("run_id", ogr.OFTInteger),
         ("ogr_t_stamp", ogr.OFTDateTime),
        )
    ),
    
    "COMMENT_POINTS": LayerDefinition(
        "f_comment_points", ogr.wkbPoint,
        (("comment", ogr.OFTString),
         ("action", ogr.OFTString)
        )
    ),
    
    "COMMENT_POLYGONS": LayerDefinition(
        "f_comment_polygons", ogr.wkbPolygon,
        (("comment", ogr.OFTString),
         ("action", ogr.OFTString)
        )
    )
}


def create_local_datasource(name=None, overwrite=False):
    '''Create a local sqlite database.'''
    if name is None:
        name = FALL_BACK
    drv = ogr.GetDriverByName(FALL_BACK_FRMT)
    if overwrite:
        drv.DeleteDataSource(name)
        data_source = None
    else:
        data_source = ogr.Open(name, True)
    if data_source is None:
        print("Creating local data source for reporting.")
        data_source = drv.CreateDataSource(name, FALL_BACK_DSCO)
    create_layers(data_source, None)
    return data_source


def schema_exists(schema):
    '''Check if a schema is already existing in database.'''
    if PG_CONNECTION is None:
        raise ValueError("Define PG_CONNECTION in pg_connection.py")
    test_connection = PG_CONNECTION + " active_schema=" + schema
    data_source = ogr.Open(test_connection)
    if data_source is None:
        raise ValueError("Failed to open " + PG_CONNECTION)
    gdal.UseExceptions()
    layers_ok = True
    for key in LAYERS:
        defn = LAYERS[key]
        layer = data_source.GetLayerByName(defn.name)
        if layer is None:
            layers_ok = False
            break
    data_source = None
    gdal.DontUseExceptions()
    return layers_ok


def create_layers(data_source, schema=None, layers=None):
    '''Create layers in database'''
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(EPSG_CODE)
    gdal.UseExceptions()  # make gdal shut up...
    for key in LAYERS:
        if layers is not None and not key in layers:
            continue
        defn = LAYERS[key]
        name = defn.name
        if schema is not None:
            name = schema + "." + name
        try:
            layer = data_source.GetLayerByName(name)
        except Exception:
            layer = None

        if layer is None:
            print("Creating: " + name)
            layer = data_source.CreateLayer(name, srs, defn.geometry_type)
            for field_name, field_type in defn.field_list:
                if field_type == ogrOFTLongString:
                    # override usual layer definition mechanics
                    field_defn = ogr.FieldDefn(field_name, ogr.OFTString)
                    field_defn.SetWidth(128)
                else:
                    field_defn = ogr.FieldDefn(field_name, field_type)
                    if field_type == ogr.OFTString:
                        field_defn.SetWidth(32)

                okay = layer.CreateField(field_defn)
                assert okay == 0

    gdal.DontUseExceptions()


def create_schema(schema, layers=None):
    '''Create schema in database'''
    if PG_CONNECTION is None:
        raise ValueError("Define PG_CONNECTION in pg_connection.py")
    data_source = ogr.Open(PG_CONNECTION, True)
    if data_source is None:
        raise ValueError("Failed to open: " + PG_CONNECTION)

    print("Creating schema " + schema + " in global data source for reporting.")

    try:
        data_source.ExecuteSQL("CREATE SCHEMA " + str(schema))
    except Exception as error_msg:
        # schema might exist - even though gdal dooesn't seem to raise an
        # exception if this is the case.
        print("Exception in schema creation:")
        print(error_msg)

    create_layers(data_source, schema, layers=layers)
    data_source = None


def set_use_local(use_local):
    ''' force using a local db - no matter what... '''
    global USE_LOCAL
    USE_LOCAL = use_local


def set_datasource(data_source):
    '''Force using this datasource pr. process '''
    global DATA_SOURCE
    DATA_SOURCE = data_source


def get_output_datasource(use_local=False):
    '''The global USE_LOCAL will override the given argument.'''
    if DATA_SOURCE is not None:
        return DATA_SOURCE
    data_source = None
    if not (use_local or USE_LOCAL):
        if PG_CONNECTION is None:
            raise ValueError("PG_CONNECTION to global db is not defined")
        data_source = ogr.Open(PG_CONNECTION, True)
    else:  # less surprising behaviour rather than suddenly falling back on a local data source
        data_source = ogr.Open(FALL_BACK, True)
    return data_source

def close_datasource():
    '''Close the connection to the reporting database.'''
    global DATA_SOURCE
    DATA_SOURCE = None
    del DATA_SOURCE

# Base reporting class
class ReportBase(object):
    LAYER_DEFINITION = None
    STRING_LENGTH = 32

    def __init__(self, use_local, run_id=None):
        self.layername = self.LAYER_DEFINITION.name
 
        if DATA_SOURCE is not None:
            print("Using open data source for reporting.")
        else:
            if use_local or USE_LOCAL:
                print("Using local data source for reporting.")
            else:
                print("Using global data source for reporting.")
                if SCHEMA_NAME is not None:
                    print("Schema is: " + SCHEMA_NAME)
                    self.layername = SCHEMA_NAME + "." + self.layername
        self.data_source = get_output_datasource(use_local)
        if self.data_source is not None:
            self.layer = self.data_source.GetLayerByName(self.layername)
        else:
            msg = 'Failed to open data source - you might need to CREATE one.'
            if use_local:
                msg += ' Create a local DB with the script recreate_local_datasource.py'
            self.layer = None
            raise Warning(msg)
        if self.layer is None:
            raise Warning("Layer " + self.layername +
                          " could not be opened. Nothing will be reported.")
        else:
            self.layerdefn = self.layer.GetLayerDefn()
        if run_id is None:  # if not specified use the global one which might be set from a wrapper
            run_id = RUN_ID
        self.run_id = run_id
        print("Run id is: %s" % self.run_id)

    def _report(self, *args, **kwargs):
        if self.layer is None:
            return 1
        feature = ogr.Feature(self.layerdefn)
        for i, arg in enumerate(args):
            if arg is not None:
                defn = self.LAYER_DEFINITION.field_list[i]
                if defn[1] in (ogr.OFTString, ogrOFTLongString):
                    val = str(arg)
                elif defn[1] == ogr.OFTInteger:
                    val = int(arg)
                elif defn[1] == ogr.OFTReal:
                    val = float(arg)
                else:  # unsupported data type
                    pass
                feature.SetField(defn[0], val)
        if self.run_id is not None:
            feature.SetField("run_id", self.run_id)
        if self.layerdefn.GetFieldIndex("ogr_t_stamp") > 0:
            date = datetime.datetime.now()
            feature.SetField(
                "ogr_t_stamp",
                date.year,
                date.month,
                date.day,
                date.hour,
                date.minute,
                date.second,
                1,
            )
        # geom given by keyword wkt_geom or ogr_geom, we do not seem to need wkb_geom...
        geom = None
        if "ogr_geom" in kwargs:
            geom = kwargs["ogr_geom"]
        elif "wkt_geom" in kwargs:
            geom = ogr.CreateGeometryFromWkt(kwargs["wkt_geom"])
        if geom is not None:
            feature.SetGeometry(geom)
        res = self.layer.CreateFeature(feature)
        if res != 0:
            # fail utterly - better to rerun that tile...
            raise Exception("Failed to create feature - check connection!")
        return res
    # args must come in the order defined by layer definition above, geom
    # given in kwargs as ogr_geom og wkt_geom

    def report(self, *args, **kwargs):
        # Method to override for subclasses...
        return self._report(*args, **kwargs)

# The design here is not too smart, but it works for now.
# Let pylint focus on the real issues:
#pylint: disable=too-few-public-methods
#pylint: disable=missing-docstring

class ReportClassCheck(ReportBase):
    LAYER_DEFINITION = LAYERS["CLASS_CHECK"]


class ReportClassCount(ReportBase):
    LAYER_DEFINITION = LAYERS["CLASS_COUNT"]


class ReportZcheckAbs(ReportBase):
    LAYER_DEFINITION = LAYERS["Z_CHECK_ABS"]


class ReportZcheckAbsGCP(ReportBase):
    LAYER_DEFINITION = LAYERS["Z_CHECK_GCP"]


class ReportLineOutliers(ReportBase):
    LAYER_DEFINITION = LAYERS["Z_LINE_OUTLIERS"]


class ReportRoofridgeCheck(ReportBase):
    LAYER_DEFINITION = LAYERS["ROOFRIDGE_ALIGNMENT"]


class ReportRoofridgeStripCheck(ReportBase):
    LAYER_DEFINITION = LAYERS["ROOFRIDGE_STRIPS"]


class ReportBuildingAbsposCheck(ReportBase):
    LAYER_DEFINITION = LAYERS["BUILDING_ABSPOS"]


class ReportBuildingRelposCheck(ReportBase):
    LAYER_DEFINITION = LAYERS["BUILDING_RELPOS"]


class ReportDensity(ReportBase):
    LAYER_DEFINITION = LAYERS["DENSITY"]


class ReportZcheckRoad(ReportBase):
    LAYER_DEFINITION = LAYERS["Z_CHECK_ROAD"]


class ReportZcheckBuilding(ReportBase):
    LAYER_DEFINITION = LAYERS["Z_CHECK_BUILD"]


class ReportAutoBuilding(ReportBase):
    LAYER_DEFINITION = LAYERS["AUTO_BUILDING"]


class ReportClouds(ReportBase):
    LAYER_DEFINITION = LAYERS["CLOUDS"]


class ReportDeltaRoads(ReportBase):
    LAYER_DEFINITION = LAYERS["DELTA_ROADS"]


class ReportSpikes(ReportBase):
    LAYER_DEFINITION = LAYERS["SPIKES"]


class ReportSteepTriangles(ReportBase):
    LAYER_DEFINITION = LAYERS["STEEP_TRIANGLES"]


class ReportWobbly(ReportBase):
    LAYER_DEFINITION = LAYERS["WOBBLY_WATER"]


class ReportHoles(ReportBase):
    LAYER_DEFINITION = LAYERS["HOLES"]


class ReportHolePoints(ReportBase):
    LAYER_DEFINITION = LAYERS["HOLE_POINTS"]


class ReportZStatsInPolygon(ReportBase):
    LAYER_DEFINITION = LAYERS["POLY_Z_STATS"]

class ReportUniqueDates(ReportBase):
    LAYER_DEFINITION = LAYERS["TIME_STATS"]
