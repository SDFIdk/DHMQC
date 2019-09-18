
from __future__ import absolute_import
from __future__ import print_function
import sys,os,time
#import some relevant modules...
from .thatsDEM import pointcloud, vector_io, array_geometry,grid
from .db import report
from osgeo import ogr
import numpy as np
#import pyspatialite.dbapi2 as db
import psycopg2 as db
from . import dhmqc_constants as constants
from .utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
GEOID_GRID=os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b_utm32.tif")
cut_to=[constants.terrain,constants.water]
CS=0.4 #cellsize for testing point distance
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")
#BEWARE:
#The same lake might be handled simultaneously by multiple processes - one might deem it invalid while another will deem it valid. 
#UPDATE: This is now handled by optimistic locking
#Argument handling is a bit quirky here - because we also want to be able to perform db-setup and las_file MUST be given as first arg to conform with qc_wrap
parser=ArgumentParser(description="Set lake heights from pointcloud data.",prog=progname)

parser.add_argument("las_file",help="input 1km las tile. If las_file ==__db__ and running as __main__: perform db actions.")
parser.add_argument("db_connection",help="input reference data in the form of a psycopg2 connection string.")
parser.add_argument("tablename",help="input name of lake layer.")
parser.add_argument("-geometry_column",dest="GEOMETRY_",help="name of geometry column name",default="wkb_geometry")
parser.add_argument("-id_attr",dest="IDATTR_",help="name of unique id attribute.",default="ogc_fid")
parser.add_argument("-burn_z_attr",dest="BURN_Z_",help="name of burn_z attribute.",default="burn_z")
parser.add_argument("-n_used_attr",dest="N_USED_",help="name of n_used attribute",default="n_used")
parser.add_argument("-is_invalid_attr",dest="IS_INVALID_",help="name of is_valid attribute",default="is_invalid")
parser.add_argument("-has_voids_attr",dest="HAS_VOIDS_",help="name of attr to specify if there are empty cells",default="has_voids")
parser.add_argument("-reason_attr",dest="REASON_",help="name of reason for invalidity / comment attr.",default="reason")
parser.add_argument("-version_attr",dest="VERSION_",help="name of version attr for optimistic locking",default="version")
parser.add_argument("-dryrun",action="store_true",help="Simply show sql commands... nothing else...")
parser.add_argument("-db_action",choices=["reset","setup"],help="Reset or create attrs. Can only be done as __main__")
parser.add_argument("-verbose",action="store_true",help="Be a lot more verbose.")
parser.add_argument("-nowarp",action="store_true",help="Do not warp. Input pointcloud is in output height system (dvr90)")

SQL_SELECT_RELEVANT="select IDATTR_ from TABLENAME_ where ST_Area(GEOMETRY_)>16 and ST_Intersects(GEOMETRY_,ST_GeomFromText('WKT_',25832)) and (IS_INVALID_ is null or IS_INVALID_<1)"
SQL_SELECT_INDIVIDUAL="select ST_AsText(GEOMETRY_),BURN_Z_,N_USED_,HAS_VOIDS_ ,VERSION_ from TABLENAME_ where IDATTR_=%s and (IS_INVALID_ is null or IS_INVALID_<1)"
SQL_SET_INVALID="update TABLENAME_ set IS_INVALID_=1,REASON_=%s,VERSION_=%s where IDATTR_=%s" #we can set invalid even though another process has done something else to the lake
SQL_UPDATE="update TABLENAME_ set IS_INVALID_=0,BURN_Z_=%s,N_USED_=%s,HAS_VOIDS_=%s,VERSION_=%s where IDATTR_=%s and VERSION_=%s" #only setting something valid if it hasn't been updated!
SQL_RESET="update TABLENAME_ set BURN_Z_=null,IS_INVALID_=0,N_USED_=0, HAS_VOIDS_=0, VERSION_=0"
SQL_SETUP="alter table TABLENAME_ add column IS_INVALID_ smallint, add column HAS_VOIDS_ smallint, add column BURN_Z_ real, add column N_USED_ integer, add column REASON_ varchar(128), add column VERSION_ smallint" 
#TODO: create index on relevant columns!!!
SQL_COMMANDS={"select_relevant":SQL_SELECT_RELEVANT,"select_individual":SQL_SELECT_INDIVIDUAL,"set_invalid":SQL_SET_INVALID,"update":SQL_UPDATE,"reset":SQL_RESET,"setup":SQL_SETUP}

def usage():
    parser.print_help()

def set_sql_commands(pargs,wkt):
    out={}
    for key in SQL_COMMANDS:
        sql=SQL_COMMANDS[key]
        sql=sql.replace("TABLENAME_",pargs.tablename)
        sql=sql.replace("WKT_",wkt)
        for attr in ["GEOMETRY_","IDATTR_","BURN_Z_","N_USED_","IS_INVALID_","REASON_","HAS_VOIDS_","VERSION_"]:
            sql=sql.replace(attr,pargs.__dict__[attr])
        out[key]=sql
    return out
 


def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception as e:
        print((str(e)))
        return 1
    if pargs.las_file!="__db__": #hackish, but handy... see above
        kmname=constants.get_tilename(pargs.las_file)
        print(("Running %s on block: %s, %s" %(progname,kmname,time.asctime())))
        try:
            extent=constants.tilename_to_extent(kmname)
        except Exception as e:
            print("Bad tilename:")
            print((str(e)))
            return 1
        tilewkt=constants.tilename_to_extent(kmname,return_wkt=True)
        if not pargs.nowarp:
            geoid=grid.fromGDAL(GEOID_GRID,upcast=True)
    else:
        tilewkt="dummy"
    sql_commands=set_sql_commands(pargs,tilewkt)
    if pargs.dryrun:
        for key in sql_commands:
            print((key+": "+sql_commands[key]))
        return
    con=db.connect(pargs.db_connection)
    cur=con.cursor()
    if pargs.las_file=="__db__": # enter the super secret database mode
        if __name__!="__main__":
            raise ValueError("Database actions can only be performed as __main__!")
        if pargs.db_action is None:
            raise ValueError("Please specify db_action")
        if pargs.db_action=="reset":
            cmd=sql_commands["reset"]
        elif pargs.db_action=="setup":
            cmd=sql_commands["setup"]
        else:
            raise ValueError("Unknown database action "+pargs.db_action)
        cur.execute(cmd)
        con.commit()
        return
        #hmmm - should crate an index also...
    
    pc=None
    #select all lakes that intersect this tile and for which the burn h is not set,,,
    print((sql_commands["select_relevant"]))
    t1=time.clock()
    cur.execute(sql_commands["select_relevant"])
    lake_ids=cur.fetchall() #some of the same lakes might be included in another query in another process - handle this better..
    t2=time.clock()
    print(("Found %d lakes in %.3f s" %(len(lake_ids),t2-t1)))
    tg=ogr.CreateGeometryFromWkt(tilewkt)
    for lake_id in lake_ids:
        lake_id=lake_id[0]
        #use optimistic locking ... continue getting a lake until it's available.
        cur.execute(sql_commands["select_individual"],(lake_id,)) #only valid ones here - somebody else might have set it invalid in the meantime
        row=cur.fetchone()
        if row is None:
            continue
        lake_wkt,burn_z,n_used,has_voids,version=row
        lake_geom=ogr.CreateGeometryFromWkt(lake_wkt)
        lake_area=lake_geom.GetArea()
        lake_centroid=lake_geom.Centroid()
        lake_centroid_pts=np.asarray(lake_centroid.GetPoints())
        if not pargs.nowarp:
            geoid_h=geoid.interpolate(lake_centroid_pts)[0]
            print(("Geoid h is: %.2f" %geoid_h))
        else:
            geoid_h=0
        lake_buf=lake_geom.Buffer(0.4)
        lake_in_tile=lake_geom.Intersection(tg)
        intersection_area=lake_in_tile.GetArea()
        #if intersection_area/lake_area<0.15:
        #	print("Not enough area covered by tile. Dont wanna make any judgements based on that!")
        #	continue
        lake_buffer_in_tile=lake_buf.Intersection(tg)
        if pargs.verbose:
            print((lake_buffer_in_tile.GetGeometryName()))
            print((lake_buffer_in_tile.GetGeometryCount()))
        if pc is None:
            pc=pointcloud.fromAny(pargs.las_file).cut_to_class(cut_to)
        lake_extent=lake_geom.GetEnvelope()
        extent_here=[max(lake_extent[0],extent[0]),max(lake_extent[2],extent[1]),min(lake_extent[1],extent[2]),min(lake_extent[3],extent[3])]
        print(extent_here)
        cs=CS
        geo_ref=[extent_here[0],cs,0,extent_here[3],0,-cs]
        ncols=int((extent_here[2]-extent_here[0])/cs)
        nrows=int((extent_here[3]-extent_here[1])/cs)
        xy_mesh=pointcloud.mesh_as_points((nrows,ncols),geo_ref)
        z_mesh=np.zeros((xy_mesh.shape[0],),dtype=np.float64)
        pc_mesh=pointcloud.Pointcloud(xy_mesh,z_mesh)
        if pargs.verbose:
            print(("updating where ogc_fid="+str(lake_id)))
        gtype=lake_buffer_in_tile.GetGeometryType()
        if gtype==ogr.wkbMultiPolygon or gtype==ogr.wkbMultiPolygon25D:
            polys=[lake_buffer_in_tile.GetGeometryRef(i).Clone() for i in range(lake_buffer_in_tile.GetGeometryCount())]
        else:
            polys=[lake_buffer_in_tile]
        arr=array_geometry.ogrpoly2array(polys[0],flatten=True)
        pc_=pc.cut_to_polygon(arr)
        pc_mesh_=pc_mesh.cut_to_polygon(arr)
        if len(polys)>1:
            if pargs.verbose:
                print("More than one geometry...")
            for poly in polys[1:]:
                arr=array_geometry.ogrpoly2array(poly,flatten=True)
                pc_.extend(pc.cut_to_polygon(arr))
                pc_mesh_.extend(pc_mesh.cut_to_polygon(arr))
        print(("Size of buffer pc: %d" %pc_.get_size()))
        n_used_here=pc_.get_size()
        if n_used_here<200:
            if pargs.verbose:
                print("Too few points!...")
            continue
        if not pargs.nowarp:
            pc_.z-=geoid_h
        z_dvr90=np.percentile(pc_.z,12.5)
        if pargs.verbose:
            print(("z dvr90: %.2f" %z_dvr90))
        #validity tests
        is_valid=True
        reason=""
        if n_used>0: 
            dz=abs(burn_z-z_dvr90)
            if dz>0.2: 
                if n_used_here/float(n_used)>0.20 or n_used_here>1000:
                    if pargs.verbose:
                        print(("Hmm - seeems to be invalid due to large z deviation : %.2f" %dz))
                    is_valid=False
                    reason="deviation to other: %.2f" %dz
                else:
                    if pargs.verbose:   
                        print(("Hmm - deviation to already set is large: %.2f, but not many pts here, continuing." %dz)) 
                    continue
       
        if is_valid:
            z2=np.median(pc_.z)
            dz=(z2-z_dvr90)
            if dz>0.2:
                is_valid=False
                reason="internal deviation: %.2f" %dz
        if not is_valid:
            print(("Deeemed invalid: "+reason))
            #optimistic locking - increase version
            cur.execute(sql_commands["set_invalid"],(reason,version+1,lake_id))
            con.commit()
            continue
        if pargs.verbose:
            print(("Size of mesh pc: %d" %pc_mesh_.get_size()))
        if pc_mesh_.get_size()>2:
            pc_.sort_spatially(1.5)
            den=pc_.density_filter(1.5,xy=pc_mesh_.xy)
            if pargs.verbose:
                print(("Max-den %.2f, min-den: %.3f" %(den.max(),den.min())))
            voids_here=(den==0).any()
        else:
            voids_here=False
        has_voids=bool(has_voids) or voids_here
        has_voids=int(has_voids)
        if pargs.verbose:
            print(("Has voids: %d" %has_voids))
        if n_used>0:
            burn_z=((n_used)*burn_z+(z_dvr90)*n_used_here)/(n_used_here+n_used)
            n_used=n_used_here+n_used
        else:
            burn_z=z_dvr90
            n_used=n_used_here
        has_updated=False
        while not has_updated:
            cur.execute(sql_commands["update"],(burn_z,n_used,has_voids,version+1,lake_id,version))
            if cur.rowcount!=1: # we failed because somebody else increased version! Reiterate
                print("Someone else got there first!")
                #select and test validity again
                cur.execute(sql_commands["select_individual"],(lake_id,)) #only valid ones here - somebody else might have set it invalid in the meantime
                row=cur.fetchone()
                if row is None:
                    break #break and continue at end
                #internal deviation is ok - so only need to test deviation to other!
                lake_wkt,burn_z,n_used,has_voids,version=row
                if n_used>0: 
                    dz=abs(burn_z-z_dvr90)
                    if dz>0.2: 
                        if n_used_here/float(n_used)>0.20 or n_used_here>1000:
                            if pargs.verbose:
                                print(("Hmm - seeems to be invalid due to large z deviation : %.2f" %dz))
                            is_valid=False
                            reason="deviation to other: %.2f" %dz
                            cur.execute(sql_commands["set_invalid"],(reason,version+1,lake_id))
                            con.commit()
                            break
                #recalculate all attrs
                has_voids=bool(has_voids) or voids_here
                has_voids=int(has_voids)
                if pargs.verbose:
                    print(("Has voids: %d" %has_voids))
                if n_used>0:
                    burn_z=((n_used)*burn_z+(z_dvr90)*n_used_here)/(n_used_here+n_used)
                    n_used=n_used_here+n_used
                else:
                    burn_z=z_dvr90
                    n_used=n_used_here
            else:
                if pargs.verbose:
                    print("Update succeded!")
                has_updated=True
        if has_updated:
            con.commit()
    return 0

if __name__=="__main__":
    main(sys.argv)
        
