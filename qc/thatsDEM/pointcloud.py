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
############################
##  Pointcloud utility class - wraps many useful methods
##
############################

import sys,os 
import numpy as np
from osgeo import gdal
import triangle, slash
#should perhaps not be done for the user behind the curtains?? Might copy data!
from array_factory import point_factory, z_factory, int_array_factory 
import array_geometry
import vector_io
#Should perhaps be moved to method in order to speed up import...
import grid
from math import ceil
from . import remote_files


def fromAny(path,**kwargs):
    #TODO - handle keywords properly - all methods, except fromLAS, will only return xyz for now. Fix this...
    b,ext=os.path.splitext(path)
    #we could use /vsi<whatever> like GDAL to signal special handling - however keep it simple for now.
    temp_file=None
    if path.startswith("s3://") or path.startswith("http://"):
        temp_file=remote_files.get_local_file(path)
        path=temp_file
    try:
        if ext==".las" or ext==".laz":
            pc=fromLAS(path,**kwargs)
        elif ext==".npy":
            pc=fromNpy(path,**kwargs)
        elif ext==".txt":
            pc=fromText(path,**kwargs)
        elif ext==".tif" or ext==".tiff" or ext==".asc":
            pc=fromGrid(path,**kwargs)
        elif ext==".bin":
            pc=fromBinary(path,**kwargs)
        elif ext==".patch":
            pc=fromPatch(path,**kwargs) #so we can look at patch-files...
        else:
            pc=fromOGR(path,**kwargs)
    except Exception as e:
        if temp_file is not None and os.path.exists(temp_file):
            os.remove(temp_file)
        raise e
    if temp_file is not None and os.path.exists(temp_file):
        os.remove(temp_file)
    return pc
            

#read a las file and return a pointcloud - spatial selection by xy_box (x1,y1,x2,y2) and / or z_box (z1,z2) and/or list of classes...
def fromLAS(path,include_return_number=False,xy_box=None, z_box=None, cls=None, **kwargs):
    plas=slash.LasFile(path)
    if (xy_box is not None) or (z_box is not None) or (cls is not None): #set filtering mask - will need to loop through twice... 
        plas.set_mask(xy_box,z_box,cls)
    r=plas.read_records(return_ret_number=include_return_number)
    plas.close()
    return Pointcloud(r["xy"],r["z"],r["c"],r["pid"],r["rn"])  #or **r would look more fancy

def fromNpy(path,**kwargs):
    xyz=np.load(path)
    return Pointcloud(xyz[:,0:2],xyz[:,2])


def fromPatch(path,**kwargs):
    xyzcpc=np.fromfile(path,dtype=np.float64)
    n=xyzcpc.size
    assert(n%6==0)
    n_recs=int(n/6)
    xyzcpc=xyzcpc.reshape((n_recs,6))
    #use new class as class
    return Pointcloud(xyzcpc[:,:2],xyzcpc[:,2],c=xyzcpc[:,5].astype(np.int32),pid=xyzcpc[:,4].astype(np.int32))

def fromBinary(path,**kwargs):
    #This is the file format we have decided to use for communicating with haystack.exe
    #actually a patch file is xyzcpc (last c is 'new-class')
    xyzcp=np.fromfile(path,dtype=np.float64)
    n=xyzcp.size
    assert(n%5==0)
    n_recs=int(n/5)
    xyzcp=xyzcp.reshape((n_recs,5))
    return Pointcloud(xyzcp[:,:2],xyzcp[:,2],c=xyzcp[:,3].astype(np.int32),pid=xyzcp[:,4].astype(np.int32))


def mesh_as_points(shape,geo_ref):
    x=geo_ref[0]+geo_ref[1]*0.5+np.arange(0,shape[1])*geo_ref[1]
    y=geo_ref[3]+geo_ref[5]*0.5+np.arange(0,shape[0])*geo_ref[5]
    x,y=np.meshgrid(x,y)
    xy=np.column_stack((x.flatten(),y.flatten()))
    assert(xy.shape[0]==shape[0]*shape[1])
    return xy

def fromArray(z,geo_ref,nd_val=None):
    xy=mesh_as_points(z.shape,geo_ref)
    z=z.flatten()
    if nd_val is not None:
        M=(z!=nd_val)
        if not M.all():
            xy=xy[M]
            z=z[M]
    return Pointcloud(xy,z)
    
#make a (geometric) pointcloud from a grid
def fromGrid(path,**kwargs):
    ds=gdal.Open(path)
    geo_ref=ds.GetGeoTransform()
    nd_val=ds.GetRasterBand(1).GetNoDataValue()
    z=ds.ReadAsArray().astype(np.float64)
    ds=None
    return fromArray(z,geo_ref,nd_val)
    

#make a (geometric) pointcloud from a (xyz) text file 
def fromText(path,delim=None,**kwargs):
    points=np.loadtxt(path,delimiter=delim)
    if points.ndim==1:
        points=points.reshape((1,3))
    return Pointcloud(points[:,:2],points[:,2])

#make a (geometric) pointcloud form an OGR readable point datasource. TODO: handle multipoint features....
def fromOGR(path,layername=None,layersql=None,extent=None):
    geoms=vector_io.get_geometries(path,layername,layersql,extent)
    points=array_geometry.ogrpoints2array(geoms)
    if points.ndim==1:
        points=points.reshape((1,3))
    return Pointcloud(points[:,:2],points[:,2])


def empty_like(pc):
    out=Pointcloud(np.empty((0,2),dtype=np.float64),np.empty((0,),dtype=np.float64))
    for a in ["c","pid","rn"]:
        if pc.__dict__[a] is not None:
            out.__dict__[a]=np.empty((0,),dtype=np.int32)
    return out

class Pointcloud(object):
    """
    Pointcloud class constructed from a xy and a z array. Optionally also classification and point source id integer arrays
    """
    def __init__(self,xy,z,c=None,pid=None,rn=None):
        self.xy=point_factory(xy)
        self.z=z_factory(z)
        if z.shape[0]!=xy.shape[0]:
            raise ValueError("z must have length equal to number of xy-points")
        self.c=int_array_factory(c) 
        self.rn=int_array_factory(rn)
        self.pid=int_array_factory(pid)
        self.triangulation=None
        self.triangle_validity_mask=None
        self.bbox=None  #[x1,y1,x2,y2]
        self.index_header=None
        self.spatial_index=None
        #TODO: implement attributte handling nicer....
        self.pc_attrs=["xy","z","c","pid","rn"]
    
    def extend(self,other,least_common=False):
        #Other must have at least as many attrs as this... rather than unexpectedly deleting attrs raise an exception, or what... time will tell what the proper implementation is...
        if not isinstance(other,Pointcloud):
            raise ValueError("Other argument must be a Pointcloud")
        for a in self.pc_attrs:
            if (self.__dict__[a] is not None) and (other.__dict__[a] is None):
                if not least_common:
                    raise ValueError("Other pointcloud does not have attributte "+a+" which this has...")
                else:
                    self.__dict__[a]=None #delete attr
        #all is well and we continue - garbage collect previous deduced objects...
        self.clear_derived_attrs()
        for a in self.pc_attrs:
            if self.__dict__[a] is not None:
                self.__dict__[a]=np.require(np.concatenate((self.__dict__[a],other.__dict__[a])), requirements=['A', 'O', 'C'])
            
    
    def might_overlap(self,other):
        return self.might_intersect_box(other.get_bounds())
    
    def might_intersect_box(self,box): #box=(x1,y1,x2,y2)
        if self.xy.shape[0]==0 or box is None:
            return False
        b1=self.get_bounds()
        xhit=box[0]<=b1[0]<=box[2] or  b1[0]<=box[0]<=b1[2]
        yhit=box[1]<=b1[1]<=box[3] or  b1[1]<=box[1]<=b1[3]
        return xhit and yhit
    
    #Properties - nice shortcuts
    @property
    def bounds(self):
        return self.get_bounds()
    @property
    def size(self):
        return self.get_size()
    @property
    def z_bounds(self):
        return self.get_z_bounds()
    @property
    def extent(self):
        if self.xy.shape[0]>0:
            bbox=self.get_bounds()
            z1,z2=self.get_z_bounds()
            extent=np.zeros((6,),dtype=np.float64)
            extent[0:2]=bbox[0:2]
            extent[3:5]=bbox[2:4]
            extent[2]=z1
            extent[5]=z2
            return extent
        return None
    def get_bounds(self):
        if self.bbox is None:
            if self.xy.shape[0]>0:
                self.bbox=array_geometry.get_bounds(self.xy)
            else:
                return None
        return self.bbox
    
    def get_z_bounds(self):
        if self.z.size>0:
            return np.min(self.z),np.max(self.z)
        else:
            return None
    def get_size(self):
        return self.xy.shape[0]
    def get_classes(self):
        if self.c is not None:
            return np.unique(self.c)
        else:
            return []
    def get_strips(self):
        return self.get_pids()
    def get_pids(self):
        if self.pid is not None:
            return np.unique(self.pid)
        else:
            return []
    def get_return_numbers(self):
        if self.rn is not None:
            return np.unique(self.rn)
        else:
            return []
    def thin(self,I):
        #modify in place
        self.clear_derived_attrs()
        for a in self.pc_attrs:
            attr=self.__dict__[a]
            if attr is not None:
                self.__dict__[a]=np.require(attr[I],requirements=['A', 'O', 'C'])
    def cut(self,mask):
        if self.xy.size==0: #just return something empty to protect chained calls...
            return empty_like(self)
        pc=Pointcloud(self.xy[mask],self.z[mask])
        for a in ["c","pid","rn"]:
            attr=self.__dict__[a]
            if attr is not None:
                pc.__dict__[a]=attr[mask]
        return pc
    def cut_to_polygon(self,rings):
        I=array_geometry.points_in_polygon(self.xy,rings)
        return self.cut(I)
    def cut_to_line_buffer(self,vertices,dist):
        I=array_geometry.points_in_buffer(self.xy,vertices,dist)
        return self.cut(I)
    def cut_to_box(self,xmin,ymin,xmax,ymax):
        I=np.logical_and((self.xy>=(xmin,ymin)),(self.xy<=(xmax,ymax))).all(axis=1)
        return self.cut(I)
    def get_grid_mask(self,M,georef):
        ac=((self.xy-(georef[0],georef[3]))/(georef[1],georef[5])).astype(np.int32)
        N=np.logical_and(ac>=(0,0),ac<(M.shape[1],M.shape[0])).all(axis=1)
        ac=ac[N]
        MM=np.zeros((self.xy.shape[0],),dtype=np.bool)
        MM[N]=M[ac[:,1],ac[:,0]]
        return MM
    def cut_to_grid_mask(self,M,georef):
        MM=self.get_grid_mask(M,georef)
        return self.cut(MM)
    def cut_to_class(self,c,exclude=False):
        #will now accept a list or another iterable...
        if self.c is not None:
            try:
                cs=iter(c)
            except:
                cs=(c,)
            if exclude:
                I=np.ones((self.c.shape[0],),dtype=np.bool)
            else:
                I=np.zeros((self.c.shape[0],),dtype=np.bool)
            #TODO: use inplace operations to speed up...
            for this_c in cs:
                if exclude:
                    I&=(self.c!=this_c)
                else:
                    I|=(self.c==this_c)
            return self.cut(I)
        return None
    def cut_to_return_number(self,rn):
        if self.rn is not None:
            I=(self.rn==rn)
            return self.cut(I)
        return None
    def cut_to_z_interval(self,zmin,zmax):
        I=np.logical_and((self.z>=zmin),(self.z<=zmax))
        return self.cut(I) 
    def cut_to_strip(self,id):
        if self.pid is not None:
            I=(self.pid==id)
            return self.cut(I)
        else:
            return None
    def triangulate(self):
        if self.triangulation is None:
            if self.xy.shape[0]>2:
                self.triangulation=triangle.Triangulation(self.xy)
            else:
                raise ValueError("Less than 3 points - unable to triangulate.")
    def set_validity_mask(self,mask):
        if self.triangulation is None:
            raise Exception("Triangulation not created yet!")
        if mask.shape[0]!=self.triangulation.ntrig:
            raise Exception("Invalid size of triangle validity mask.")
        self.triangle_validity_mask=mask
    def clear_validity_mask(self):
        self.triangle_validity_mask=None
    def calculate_validity_mask(self,max_angle=45,tol_xy=2,tol_z=1):
        tanv2=np.tan(max_angle*np.pi/180.0)**2
        geom=self.get_triangle_geometry()
        self.triangle_validity_mask=(geom<(tanv2,tol_xy,tol_z)).all(axis=1)
    def get_validity_mask(self):
        return self.triangle_validity_mask
    def get_grid(self,ncols=None,nrows=None,x1=None,x2=None,y1=None,y2=None,cx=None,cy=None,nd_val=-999,crop=0,method="triangulation"):
        #xl = left 'corner' of "pixel", not center.
        #yu= upper 'corner', not center.
        #returns grid and gdal style georeference...
        
        #TODO: fix up logic below...
        if x1 is None:
            bbox=self.get_bounds()
            x1=bbox[0]+crop
        if x2 is None:
            bbox=self.get_bounds()
            x2=bbox[2]-crop
        if y1 is None:
            bbox=self.get_bounds()
            y1=bbox[1]+crop
        if y2 is None:
            bbox=self.get_bounds()
            y2=bbox[3]-crop
        if ncols is None and cx is None:
            raise ValueError("Unable to compute grid extent from input data")
        if nrows is None and cy is None:
            raise ValueError("Unable to compute grid extent from input data")
        if ncols is None:
            ncols=int(ceil((x2-x1)/cx))
        else:
            cx=(x2-x1)/float(ncols)
        if nrows is None:
            nrows=int(ceil((y2-y1)/cy))
        else:
            cy=(y2-y1)/float(nrows)
        #geo ref gdal style...
        geo_ref=[x1,cx,0,y2,0,-cy]
        if method=="triangulation": #should be special method not to mess up earlier code...
            if self.triangulation is None:
                raise Exception("Create a triangulation first...")
            g=self.triangulation.make_grid(self.z,ncols,nrows,x1,cx,y2,cy,nd_val,return_triangles=False)
            return grid.Grid(g,geo_ref,nd_val)
        elif method=="return_triangles":
            if self.triangulation is None:
                raise Exception("Create a triangulation first...")
            g,t=self.triangulation.make_grid(self.z,ncols,nrows,x1,cx,y2,cy,nd_val,return_triangles=True)
            return grid.Grid(g,geo_ref,nd_val),grid.Grid(t,geo_ref,nd_val)
        elif method=="density": #density grid
            arr_coords=((self.xy-(geo_ref[0],geo_ref[3]))/(geo_ref[1],geo_ref[5])).astype(np.int32)
            M=np.logical_and(arr_coords[:,0]>=0, arr_coords[:,0]<ncols)
            M&=np.logical_and(arr_coords[:,1]>=0,arr_coords[:,1]<nrows)
            arr_coords=arr_coords[M]
            # Wow - this gridding is sooo simple! and fast!
            #create flattened index
            B=arr_coords[:,1]*ncols+arr_coords[:,0]
            bins=np.arange(0,ncols*nrows+1)
            h,b=np.histogram(B,bins)
            h=h.reshape((nrows,ncols))
            return grid.Grid(h,geo_ref,0) #zero always nodata value here...
        elif method=="class":
            #define method which takes the most frequent value in a cell... could be only mean...
            g=grid.grid_most_frequent_value(self.xy,self.c,ncols,nrows,geo_ref,nd_val=-999)
            g.grid=g.grid.astype(np.uint8)
            return g
        elif method=="pid":
            g=grid.grid_most_frequent_value(self.xy,self.pid,ncols,nrows,geo_ref,nd_val=-999)
            return g
        else:
            raise ValueError("Unsupported method.")
    def find_triangles(self,xy_in,mask=None):
        if self.triangulation is None:
            raise Exception("Create a triangulation first...")
        xy_in=point_factory(xy_in)
        #-2 indices signals outside triangulation, -1 signals invalid, else valid
        return self.triangulation.find_triangles(xy_in,mask)
        
    def find_appropriate_triangles(self,xy_in,mask=None):
        if mask is None:
            mask=self.triangle_validity_mask
        if mask is None:
            raise Exception("This method needs a triangle validity mask.")
        return self.find_triangles(xy_in,mask)
    
    def get_points_in_triangulation(self,xy_in):
        I=find_triangles(xy_in)
        return xy_in[I>=0]
        
    def get_points_in_valid_triangles(self,xy_in,mask=None):
        I=find_appropriate_triangles(self,xy_in,mask)
        return xy_in[I>=0]
    
    def get_boundary_vertices(self,M_t,M_p): #hmmm - find the vertices which are marked by M_p and in triangles marked by M_t
        M_out=array_geometry.get_boundary_vertices(M_t,M_p,self.triangulation.vertices)
        return M_out
        
    def interpolate(self,xy_in,nd_val=-999,mask=None):
        if self.triangulation is None:
            raise Exception("Create a triangulation first...")
        xy_in=point_factory(xy_in)
        return self.triangulation.interpolate(self.z,xy_in,nd_val,mask)
    #Interpolates points in valid triangles
    def controlled_interpolation(self,xy_in,mask=None,nd_val=-999):
        if mask is None:
            mask=self.triangle_validity_mask
        if mask is None:
            raise Exception("This method needs a triangle validity mask.")
        return self.interpolate(xy_in,nd_val,mask)
        
    def get_triangle_geometry(self):
        if self.triangulation is None:
            raise Exception("Create a triangulation first...")
        return array_geometry.get_triangle_geometry(self.xy,self.z,self.triangulation.vertices,self.triangulation.ntrig)
    def warp(self,sys_in,sys_out):
        pass #TODO - use TrLib
    def toE(self,geoid):
        #warp to ellipsoidal heights
        toE=geoid.interpolate(self.xy)
        assert((toE!=geoid.nd_val).all())
        self.z+=toE
    def toH(self,geoid):
        #warp to orthometric heights
        toE=geoid.interpolate(self.xy)
        assert((toE!=geoid.nd_val).all())
        self.z-=toE
    def set_class(self,c):
        self.c=np.ones(self.z.shape,dtype=np.int32)*c
    #dump methods
    def dump_csv(self,f,callback=None):
        #dump as a csv-file - this is gonna be slow. TODO: refactor a bit...
        f.write("x,y,z")
        has_c=False
        if self.c is not None:
            f.write(",c")
            has_c=True
        has_id=False
        if self.pid is not None:
            f.write(",strip")
            has_id=True
        f.write("\n")
        n=self.get_size()
        for i in xrange(n):
            f.write("{0:.2f},{1:.2f},{2:.2f}".format(self.xy[i,0],self.xy[i,1],self.z[i]))
            if has_c:
                f.write(",{0:d}".format(self.c[i]))
            if has_id:
                f.write(",{0:d}".format(self.pid[i]))
            f.write("\n")
            if callback is not None and i>0 and i%1e4==0:
                callback(i)
    def dump_txt(self,path):
        xyz=np.column_stack((self.xy,self.z))
        np.savetxt(path,xyz)
    def dump_npy(self,path):
        xyz=np.column_stack((self.xy,self.z))
        np.save(path,xyz)
    def dump_bin(self,path):
        assert(self.c is not None)
        assert(self.pid is not None)
        xyzcp=np.column_stack((self.xy,self.z,self.c.astype(np.float64),self.pid.astype(np.float64))).astype(np.float64)
        xyzcp.tofile(path)
    def sort_spatially(self,cs,shape=None,xy_ul=None):
        if self.get_size()==0:
            raise Exception("No way to sort an empty pointcloud.")
        if (bool(shape)!=bool(xy_ul)): #either both None or both given
            raise ValueError("Neither or both of shape and xy_ul should be specified.")
        self.clear_derived_attrs()
        if shape is None:
            x1,y1,x2,y2=self.get_bounds()
            ncols=int((x2-x1)/cs)+1
            nrows=int((y2-y1)/cs)+1
        else:
            x1,y2=xy_ul
            nrows,ncols=shape
        arr_coords=((self.xy-(x1,y2))/(cs,-cs)).astype(np.int32)
        #do we cover the whole area?
        mx,my=arr_coords.min(axis=0)
        Mx,My=arr_coords.max(axis=0)
        assert(min(mx,my)>=0 and Mx<ncols and My<nrows)
        B=arr_coords[:,1]*ncols+arr_coords[:,0]
        I=np.argsort(B)
        B=B[I]
        self.spatial_index=np.ones((ncols*nrows*2,),dtype=np.int32)*-1
        res=array_geometry.lib.fill_spatial_index(B,self.spatial_index,B.shape[0],ncols*nrows)
        if  res!=0:
            raise Exception("Size of spatial index array too small! Programming error!")
        for a in self.pc_attrs:
            attr=self.__dict__[a]
            if attr is not None:
                self.__dict__[a]=attr[I]
        self.index_header=np.asarray((ncols,nrows,x1,y2,cs),dtype=np.float64)
        return self
        
    def clear_derived_attrs(self):
        #Clears attrs which become invalid by an extentsion or sorting
        self.triangulation=None
        self.index_header=None
        self.spatial_index=None
        self.bbox=None
        self.triangle_validity_mask=None
    #Filterering methods below...
    def validate_filter_args(self,rad):
        if self.spatial_index is None:
            raise Exception("Build a spatial index first!")
        if rad>self.index_header[4]:
            raise Warning("Filter radius larger than cell size of spatial index will not catch all points!")
    def min_filter(self, filter_rad,xy=None, nd_val=-9999):
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_min_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def mean_filter(self, filter_rad, xy=None, nd_val=-9999):
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_mean_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def max_filter(self,filter_rad,xy=None,nd_val=-9999):
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_min_filter(xy,self.xy,-self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return -z_out
    def median_filter(self, filter_rad, xy=None,nd_val=-9999):
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_median_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def var_filter(self, filter_rad, xy=None, nd_val=-9999):
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_var_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def distance_filter(self, filter_rad,xy=None,nd_val=9999):
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_distance_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def density_filter(self, filter_rad, xy=None):
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_density_filter(xy,self.xy,self.z,z_out,filter_rad,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def idw_filter(self,filter_rad,xy=None,nd_val=-9999):
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_idw_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def spike_filter(self, filter_rad,tanv2,zlim=0.2):
        self.validate_filter_args(filter_rad)
        if (tanv2<0 or zlim<0):
            raise ValueError("Spike parameters must be positive!")
        z_out=np.empty_like(self.z)
        array_geometry.lib.pc_spike_filter(self.xy,self.z,self.xy,self.z,z_out,filter_rad,tanv2,zlim,self.spatial_index,self.index_header,self.xy.shape[0])
        return z_out
    
    
    
    


def unit_test(path):
    print("Reading all")
    pc1=fromLAS(path)
    extent=pc1.get_bounds()
    rx=extent[2]-extent[0]
    ry=extent[3]-extent[1]
    rx*=0.2
    ry*=0.2
    crop=extent+(rx,ry,-rx,-ry)
    pc1=pc1.cut_to_box(*crop)
    print("Reading filtered")
    pc2=fromLAS(path,xy_box=crop)
    assert(pc1.get_size()==pc2.get_size())
    assert((pc1.get_classes()==pc2.get_classes()).all())
    pc1.sort_spatially(1)
    assert((pc1.get_classes()==pc2.get_classes()).all())
    pc2.sort_spatially(1)
    z1=pc1.min_filter(1)
    z2=pc2.min_filter(1)
    assert((z1==z2).all())
    assert((z1<=pc1.z).all())
    return 0



    
        
        
