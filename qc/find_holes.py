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
import sys,os,time
#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry, grid
from db import report
import numpy as np
import scipy.ndimage as image
import  dhmqc_constants as constants
from utils.osutils import ArgumentParser  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
from osgeo import osr
import json
EPSG_CODE=25832 #default srs
SRS=osr.SpatialReference()
SRS.ImportFromEPSG(EPSG_CODE)
SRS_WKT=SRS.ExportToWkt()
TILE_SIZE=constants.tile_size #should be 1km tiles...
#DELICATE BALANCE HERE
FRAD=3
PDIST_LIM=1.8 #only large holes
DEN_LIM=1.0
CS_BURN=1.6
CS_MESH=1.6
FRAD_IDW=2
BUF_RAD=2.5
CS_FINAL_GRID=1.0
FRAD_FINAL_GRID=2.5
MAX_AREA=250*250 #areas larger than this will only be marked - something else must be wrong!

cut_to=[constants.terrain,constants.water,constants.bridge]
GEOID_GRID=os.path.join(os.path.dirname(__file__),"..","data","dkgeoid13b_utm32.tif")
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")

#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Find regions with low density or large pointdistance.",prog=progname)

#add some arguments below

parser.add_argument("-class",type=int,default=5,help="Specify ground class in reference pointcloud. Defaults to 5 (dhm-2007).")
parser.add_argument("-cs",type=float,default=2.5,help="Specify gridsize for clustering points. Defaults to 2.5")
parser.add_argument("-nlim",type=int,default=8,help="Specify limit for number of points an interesting 'patch' must contain. Defaults to 8.")
parser.add_argument("-area",type=float,default=30,help="Specify area limit for an interesting 'patch' defaults to 30.")
parser.add_argument("-nowarp",action="store_true",help="If ref. pointcloud is in same height system as input, use this option.")
parser.add_argument("-expansions",type=int,default=4,help="Number of 'expansion' steps of polygons in order to avoid small disconnected parts. Deault 4")
parser.add_argument("-dbpoints",action="store_true",help="Also report points to db - warning, can be many points!")
parser.add_argument("-dontapply",action="store_true",help="Do not apply dz to patching points automatically.")
parser.add_argument("-debug",action="store_true",help="Turn on some more verbosity.")
db_group=parser.add_mutually_exclusive_group()
db_group.add_argument("-use_local",action="store_true",help="Force use of local database for reporting.")
db_group.add_argument("-schema",help="Specify schema for PostGis db.")

parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("ref_data",help="input reference data connection string (e.g to a db, or just a path to a shapefile).")
parser.add_argument("json_params",help="Parameter file with db-connections to rasterise reference vector layers.")
parser.add_argument("outdir",help="Output directory to dump xyz files into.")

#PARAMETER FILE MUST DEFINE
NAMES=["MAP_CONNECTION","EXCLUDE_SQL"]
#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
def usage():
    parser.print_help()

#PHILOSOPHY:
#New terrain pts under buildings, forests etc are not problematic for a surface model, as long as we set return_number>1 or some synthetic class !!!!!
#YEAH

def cluster(pc,cs,n_expand=2):
    #cluster according to some scheme and return a segmentizeed grid
    x1,y1,x2,y2=pc.get_bounds()
    georef=[x1-cs,cs,0,y2+cs,0,-cs]
    ncols=int((x2-georef[0])/cs)+1
    nrows=int((georef[3]-y1)/cs)+1
    JI=((pc.xy-(georef[0],georef[3]))/(georef[1],georef[5])).astype(np.int64)
    assert((JI>=0).all())
    assert((JI<(ncols,nrows)).all())
    M=np.zeros((nrows,ncols),dtype=np.bool)
    M[JI[:,1],JI[:,0]]=1
    for i in range(n_expand):
        n1=M.sum()
        M=array_geometry.binary_fill_gaps(M)
        n2=M.sum()
        print("Before expansion: %d, after expansion: %d" %(n1,n2))
        if n2==n1:
            break
    return M,georef
        

def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception,e:
        print(str(e))
        return 1
    kmname=constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
    
    try:
        extent=constants.tilename_to_extent(kmname)
    except Exception,e:
        print("Bad tilename:")
        print(str(e))
        return 1
    if pargs.json_params.endswith(".json"):
        with open(pargs.json_params) as f:
            fargs=json.load(f)
    else:
        fargs=json.loads(pargs.json_params)
    
    for name in NAMES: #test for defined names
        assert(name in fargs)
    
    
    if pargs.schema is not None:
        report.set_schema(pargs.schema)
    reporter_polys=report.ReportHoles(pargs.use_local)
    reporter_points=report.ReportHolePoints(pargs.use_local)
    if not os.path.exists(pargs.outdir):
        os.mkdir(pargs.outdir)
    pc=pointcloud.fromAny(pargs.las_file).cut_to_class(cut_to) #should be as a terrain grid - but problems with high veg on fields!!!
    pc_ref=pointcloud.fromAny(pargs.ref_data).cut_to_class(5)
    print("points in input-cloud: %d" %pc.get_size())
    print("points in ref-cloud: %d" %pc_ref.get_size())
    if pc.get_size()<10 or pc_ref.get_size()<100:
        print("Too few points.")
        return 1
    print("Sorting...")
    pc.sort_spatially(FRAD)
    print("Filtering..")
    #so 1 of two criteria should be fullfilled: low, low, density or high pointdistance...
    d_in=pc.density_filter(FRAD,pc_ref.xy)
    pd_in=pc.distance_filter(FRAD,pc_ref.xy)
    M=np.logical_or(d_in<DEN_LIM,pd_in>PDIST_LIM)
    pc_pot=pc_ref.cut(M)
    if pc_pot.get_size()==0:
        print("No potential points.")
        return 0
    print("# potential fill points: %d" %pc_pot.get_size())
    cs_burn=CS_BURN  #use a global
    geo_ref=[extent[0],cs_burn,0,extent[3],0,-cs_burn]
    ncols=int((extent[2]-extent[0])/cs_burn)
    nrows=int((extent[3]-extent[1])/cs_burn)
    assert((cs_burn*ncols+extent[0])==extent[2])
    exclude_mask=np.zeros((nrows,ncols),dtype=np.bool)
    for sql in fargs["EXCLUDE_SQL"]:
        print("Burning "+sql+"....")
        exclude_mask|=vector_io.burn_vector_layer(fargs["MAP_CONNECTION"],geo_ref,exclude_mask.shape,layersql=sql)
    print("Excluded cells: %d" %(exclude_mask.sum()))
    include_mask=np.logical_not(exclude_mask)
    pc_pot=pc_pot.cut_to_grid_mask(include_mask,geo_ref)
    print("# potential fill points: %d" %pc_pot.get_size())
    if pc_pot.get_size()==0:
        print("No potential points.")
        return 0
    print("Taking a closer look...")
    #perhaps relax this more.... we're already looking at potential candidates...
    R=2.0
    pc_pot.sort_spatially(R)
    a=np.pi*(R**2)
    d_look=pc_pot.density_filter(R)*a
    M=d_look>1.2  # at least 2 points in rad 
    pc_pot=pc_pot.cut(M)
    print("# potential fill points: %d" %pc_pot.get_size())
    if pc_pot.get_size()==0:
        print("No potential points.")
        return 0
    print("Expanding slightly...") #Yesss - this way well get points back in...
    #we just need to expand this less than the criteria above _ perhaps split into two pointclouds not to mix up...
    R=PDIST_LIM*0.9
    pc_pot.sort_spatially(R)
    d_look=pc_pot.distance_filter(R,xy=pc_ref.xy,nd_val=9999)
    M=(d_look<R)
    pc_pot=pc_ref.cut(M)
    pc_pot=pc_pot.cut_to_grid_mask(include_mask,geo_ref)
    print("# potential fill points: %d" %pc_pot.get_size())
    #with open(os.path.join(pargs.outdir,"lowden2_"+kmname+".csv"),"w") as f:
    #	pc_pot.dump_csv(f)
    if pc_pot.get_size()>0:
        cs=CS_MESH  #use a global
        geo_ref=[extent[0],cs,0,extent[3],0,-cs]
        ncols=int((extent[2]-extent[0])/cs)
        nrows=int((extent[3]-extent[1])/cs)
        assert((cs*ncols+extent[0])==extent[2])
        pc_ref.sort_spatially(FRAD_IDW)
        pc.sort_spatially(FRAD_IDW)
        xy=pointcloud.mesh_as_points((nrows,ncols),geo_ref)
        print("idw1")
        z_new=pc.idw_filter(FRAD_IDW,xy=xy,nd_val=-9999)
        print("idw2")
        z_old=pc_ref.idw_filter(FRAD_IDW,xy=xy,nd_val=-9999)
        M=np.logical_and(z_new!=-9999,z_old!=-9999)
        pc_diff=pointcloud.Pointcloud(xy,z_new-z_old).cut(M)
        if not pargs.nowarp:
            geoid=grid.fromGDAL(GEOID_GRID,upcast=True)
            print("Using geoid from %s to warp to ellipsoidal heights." %GEOID_GRID)
            pc_diff.toH(geoid)  #well we just subtract the missing Elliposidal height part
            pc_pot.toE(geoid)
        M,geo_ref=cluster(pc_pot,pargs.cs,pargs.expansions)
        poly_ds,polys=vector_io.polygonize(M,geo_ref)
        f_name=kmname+"_"+str(int(time.time()))+".bin"
        assert(polys is not None)
        for poly in polys: #yes feature iteration should work...
            g=poly.GetGeometryRef()
            area=g.GetArea()
            if pargs.debug:
                print("Area: %.2f" %area)
            arr=array_geometry.ogrgeom2array(g)
            x1,y1=arr[0].min(axis=0)
            x2,y2=arr[0].max(axis=0)
            close_to_bd=(x1-extent[0])<1e-3 or (y1-extent[1])<1e-3 or (extent[2]-x2)<1e-3 or (extent[3]-y2)<1e-3
            if (not close_to_bd) and area<pargs.area:
                if pargs.debug:
                    print("Too small area...")
                continue
            if area>MAX_AREA:
                print("Really large hole - seriously - something else is wrong here!. Wont report points!")
                n=-9999
                z1=-9999
                z2=-9999
                dz=-9999
                sd=-9999
            else:
                M_in_poly=array_geometry.points_in_polygon(pc_pot.xy,arr) #this allows us to adjust with dz later if we want to...
                pc_=pc_pot.cut(M_in_poly)
                n=pc_.get_size()
                if pargs.debug:
                    print("#Points: %d" %n)
                #TODO: Compare to input pointcloud!
                if (not close_to_bd) and n<pargs.nlim: #perhaps include if we intersect boundary of tile...!
                    continue
                buf=g.Buffer(BUF_RAD*0.5)
                bound=np.asarray(buf.GetGeometryRef(0).GetPoints())
                buf_pc=pc_diff.cut_to_line_buffer(bound,BUF_RAD)
                n_buf=buf_pc.get_size()
                if pargs.debug:
                    print("#Mesh points in buffer: %d"%n_buf)
                if n_buf>2:
                    dz=np.median(buf_pc.z) # new - old, so add dz to old
                    sd=np.std(buf_pc.z)
                    #OK - so now we can adjust the right points:
                    if not pargs.dontapply: #control this with an option 
                        pc_pot.z[M_in_poly]+=dz
                else:
                    dz=-9999
                    sd=-9999
                z1,z2=pc_.get_z_bounds()
                if pargs.dbpoints: 
                    wkt="MULTIPOINT("
                    for pt in pc_.xy:
                        wkt+="{0:.2f} {1:.2f},".format(pt[0],pt[1])
                    wkt=wkt[:-1]+")"
                    reporter_points.report(kmname,z1,z2,dz,n,wkt_geom=wkt)
            reporter_polys.report(kmname,z1,z2,dz,sd,n,area,f_name,ogr_geom=g)
        #dump fill points
        outname=os.path.join(pargs.outdir,f_name)
        pc_pot.dump_bin(outname)
        #dump a grid...
        pc.extend(pc_pot,least_common=True)
        cs=CS_FINAL_GRID #use a global
        geo_ref=[extent[0],cs,0,extent[3],0,-cs]
        ncols=int((extent[2]-extent[0])/cs)
        nrows=int((extent[3]-extent[1])/cs)
        assert((cs*ncols+extent[0])==extent[2])
        pc.sort_spatially(FRAD_FINAL_GRID)
        xy=pointcloud.mesh_as_points((nrows,ncols),geo_ref)
        z_new=pc.idw_filter(FRAD_IDW,xy=xy,nd_val=-9999).reshape((nrows,ncols))
        g=grid.Grid(z_new,geo_ref,-9999)
        outname=os.path.join(pargs.outdir,"dtm_f_"+kmname+".tif")
        g.save(outname, dco=["TILED=YES","COMPRESS=DEFLATE"],srs=SRS_WKT)
        polys=None
        poly_ds=None


if __name__=="__main__":
    main(sys.argv)
    