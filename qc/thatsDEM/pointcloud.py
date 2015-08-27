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
    """
    Load a pointcloud from a range of 'formats'. The specific 'driver' to use is decided from the filename extension.
    Can also handle remote files from s3 and http. Whether a file is remote is decided from the path prefix.
    Args:
        path: a 'connection string'
        additional keyword arguments will be passed on to the specific format handler.
    Returns:
        A pointcloud.Pointcloud object
    """
    #TODO - handle keywords properly - all methods, except fromLAS, will only return xyz for now. Fix this...
    b,ext=os.path.splitext(path)
    #we could use /vsi<whatever> like GDAL to signal special handling - however keep it simple for now.
    temp_file=None
    if remote_files.is_remote(path):
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
    """
    Load a pointcloud from las / laz format via slash.LasFile. Laz reading currently requires that laszip-cli is findable.
    Args:
        path: path to las / laz file. 
        include_return_number: bool, indicates whether return number should be included.
        xy_box: (x1,y2,x2,y2), filter by extent in load time. Will NOT work for laz files.
        z_box: (z1,z2), filter by z-extent in load time. Will NOT work for laz files.
        cls: list of classes to filter by in load time. Will NOT work for laz files.
    Returns:
        A pointcloud.Pointcloud object.
    """
    plas=slash.LasFile(path)
    if (xy_box is not None) or (z_box is not None) or (cls is not None): #set filtering mask - will need to loop through twice... 
        plas.set_mask(xy_box,z_box,cls)
    r=plas.read_records(return_ret_number=include_return_number)
    plas.close()
    return Pointcloud(r["xy"],r["z"],r["c"],r["pid"],r["rn"])  #or **r would look more fancy

def fromNpy(path,**kwargs):
    """
    Load a pointcloud from a platform independent numpy .npy file. Will only keep xyz.
    Args:
        path: path to .npy file.
    Returns:
        A pointcloud.Pointcloud object.
    """
    xyz=np.load(path)
    return Pointcloud(xyz[:,0:2],xyz[:,2])


def fromPatch(path,**kwargs):
    """
    Load a pointcloud from a platform dependent numpy .patch file. 
    This is a 'classification remapping file' with entries x y z c1 (original class) p (source id) c2 (to class) stored as doubles.
    Will keep the output class in the returned pointcloud.
    Args:
        path: path to patch file.
    Returns:
        A pointcloud.Pointcloud object.
    """
    xyzcpc=np.fromfile(path,dtype=np.float64)
    n=xyzcpc.size
    assert(n%6==0)
    n_recs=int(n/6)
    xyzcpc=xyzcpc.reshape((n_recs,6))
    #use new class as class
    return Pointcloud(xyzcpc[:,:2],xyzcpc[:,2],c=xyzcpc[:,5].astype(np.int32),pid=xyzcpc[:,4].astype(np.int32))

def fromBinary(path,**kwargs):
    """
    Load a pointcloud from a platform dependent numpy binary file. 
    This is a binary file with entries x y z c (original class) p (source id) stored as doubles.
    Args:
        path: path to binary file.
    Returns:
        A pointcloud.Pointcloud object.
    """
    #This is the file format we originally decided to use for communicating with haystack.exe. Now using .patch files instead. 
    #A quick and dirty format. Would be better to use e.g. npy or npz platform independent files. 
    xyzcp=np.fromfile(path,dtype=np.float64)
    n=xyzcp.size
    assert(n%5==0)
    n_recs=int(n/5)
    xyzcp=xyzcp.reshape((n_recs,5))
    return Pointcloud(xyzcp[:,:2],xyzcp[:,2],c=xyzcp[:,3].astype(np.int32),pid=xyzcp[:,4].astype(np.int32))


def mesh_as_points(shape,geo_ref):
    """
    Construct a mesh of xy coordinates corresponding to the cell centers of a grid.
    Args:
        shape: (nrows,ncols)
        geo_ref: GDAL style georeference of grid.
    Returns:
        Numpy array of shape (nrows*ncols,2).
    """
    x=geo_ref[0]+geo_ref[1]*0.5+np.arange(0,shape[1])*geo_ref[1]
    y=geo_ref[3]+geo_ref[5]*0.5+np.arange(0,shape[0])*geo_ref[5]
    x,y=np.meshgrid(x,y)
    xy=np.column_stack((x.flatten(),y.flatten()))
    assert(xy.shape[0]==shape[0]*shape[1])
    return xy

def fromArray(z,geo_ref,nd_val=None):
    """
    Construct a Pointcloud object corresponding to the cell centers of an in memory grid.
    Args:
        z: Numpy array of shape (nrows,ncols).
        geo_ref: GDAL style georefence.
        nd_val: No data value of grid. Cell centers with this value will be excluded.
    Returns:
        A pointcloud.Pointcloud object
    """
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
    """
    Construct a Pointcloud object corresponding to the cell centers of the first band of a GDAL loadable raster.
    Args:
        path: GDAL connection string.
    Returns:
        A pointcloud.Pointcloud object
    """
    ds=gdal.Open(path)
    geo_ref=ds.GetGeoTransform()
    nd_val=ds.GetRasterBand(1).GetNoDataValue()
    z=ds.ReadAsArray().astype(np.float64)
    ds=None
    return fromArray(z,geo_ref,nd_val)
    

#make a (geometric) pointcloud from a (xyz) text file 
def fromText(path,delim=None,**kwargs):
    """
    Load a pointcloud (xyz) from a delimited text file.
    Args:
        path: path to file.
        delim: Delimiter, None corresponds to white space.
    Returns:
        A pointcloud.Pointcloud object containg only the raw x,y and z coords.
    """
    points=np.loadtxt(path,delimiter=delim)
    if points.ndim==1:
        points=points.reshape((1,3))
    return Pointcloud(points[:,:2],points[:,2])

#make a (geometric) pointcloud form an OGR readable point datasource. TODO: handle multipoint features....
def fromOGR(path,layername=None,layersql=None,extent=None):
    """
    Load a pointcloud from an OGR 3D-point datasource (only geometries).
    Args:
        path:  OGR connection string.
        layername: name of layer to load. Use either layername or layersql.
        layersql: sql command to execute to fetch geometries. Use either layername or layersql.
        extent: Extent to filter the result set by.
    Returns:
        A pointcloud.Pointcloud object containg only the raw x,y and z coords.
    """
    geoms=vector_io.get_geometries(path,layername,layersql,extent)
    points=array_geometry.ogrpoints2array(geoms)
    if points.ndim==1:
        points=points.reshape((1,3))
    return Pointcloud(points[:,:2],points[:,2])


def empty_like(pc):
    """
    Contruct and empty Pointcloud object with same attributes as input pointcloud.
    Args:
        pc: Pointcloud.pointcloud object.
    Returns:
        Pointcloud.pointcloud object.
    """
    out=Pointcloud(np.empty((0,2),dtype=np.float64),np.empty((0,),dtype=np.float64))
    for a in ["c","pid","rn"]:
        if pc.__dict__[a] is not None:
            out.__dict__[a]=np.empty((0,),dtype=np.int32)
    return out

class Pointcloud(object):
    """
    Pointcloud class constructed from a xy and a z array. Optionally also classification,point source id and return number integer arrays
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
        #TODO: implement attribute handling nicer....
        self.pc_attrs=["xy","z","c","pid","rn"]
    
    def extend(self,other,least_common=False):
        """
        Extend the pointcloud 'in place' by adding another pointcloud. Attributtes of current pointcloud must be a subset of attributes of other.
        Args:
            other: A pointcloud.Pointcloud object
            least_common: Not implemented.
        Raises:
            ValueError: If other pointcloud does not have at least the same attributes as self.
        """
        #Other must have at least as many attrs as this... rather than unexpectedly deleting attrs raise an exception, or what... time will tell what the proper implementation is...
        if not isinstance(other,Pointcloud):
            raise ValueError("Other argument must be a Pointcloud")
        for a in self.pc_attrs:
            if (self.__dict__[a] is not None) and (other.__dict__[a] is None):
                if not least_common:
                    raise ValueError("Other pointcloud does not have attribute "+a+" which this has...")
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
        """Return planar bounding box as (x1,y1,x2,y2) or None if empty."""
        if self.bbox is None:
            if self.xy.shape[0]>0:
                self.bbox=array_geometry.get_bounds(self.xy)
            else:
                return None
        return self.bbox
    
    def get_z_bounds(self):
        """Return z bounding box as (z1,z2) or None if empty."""
        if self.z.size>0:
            return np.min(self.z),np.max(self.z)
        else:
            return None
    def get_size(self):
        """Return point count."""
        return self.xy.shape[0]
    def get_classes(self):
        """Return the list of unique classes."""
        if self.c is not None:
            return np.unique(self.c)
        else:
            return []
    def get_strips(self):
        #just an alias
        return self.get_pids()
    def get_pids(self):
        """Return the list of unique point source ids"""
        if self.pid is not None:
            return np.unique(self.pid)
        else:
            return []
    def get_return_numbers(self):
        """Return the list of unique return numbers (rn_min,...,rn_max)"""
        if self.rn is not None:
            return np.unique(self.rn)
        else:
            return []
    def thin(self,I):
        """
        Modify the pointcloud 'in place' by slicing to a mask or index array.
        Args:
            I: Mask or index array (1d) to use for fancy numpy indexing.
        """
        #modify in place
        self.clear_derived_attrs()
        for a in self.pc_attrs:
            attr=self.__dict__[a]
            if attr is not None:
                self.__dict__[a]=np.require(attr[I],requirements=['A', 'O', 'C'])
    def cut(self,mask):
        """
        Cut the pointcloud by a mask or index array using fancy indexing.
        Args:
            mask: Mask or index array (1d) to use for fancy numpy indexing.
        Returns:
            The 'sliced' Pointcloud object.
        """
        if self.xy.size==0: #just return something empty to protect chained calls...
            return empty_like(self)
        pc=Pointcloud(self.xy[mask],self.z[mask])
        for a in ["c","pid","rn"]:
            attr=self.__dict__[a]
            if attr is not None:
                pc.__dict__[a]=attr[mask]
        return pc
    def cut_to_polygon(self,rings):
        """
        Cut the pointcloud to a polygon.
        Args:
            rings: list of rings as numpy arrays. The first entry is the outer ring, while subsequent are holes. Holes in holes not supported.
        Returns:
            A new Pointcloud object.
        """
        I=array_geometry.points_in_polygon(self.xy,rings)
        return self.cut(I)
    def cut_to_line_buffer(self,vertices,dist):
        """
        Cut the pointcloud to a buffer around a line (quite fast).
        Args:
            vertices: The vertices of the line string as a (n,2) float64 numpy array.
            dist: The buffer distance.
        Returns:
            A new Pointcloud object.
        """
        I=array_geometry.points_in_buffer(self.xy,vertices,dist)
        return self.cut(I)
    def cut_to_box(self,xmin,ymin,xmax,ymax):
        """Cut the pointcloud to a planar bounding box"""
        I=np.logical_and((self.xy>=(xmin,ymin)),(self.xy<=(xmax,ymax))).all(axis=1)
        return self.cut(I)
    def get_grid_mask(self,M,georef):
        """
        Get the boolean mask indicating which points lie within a (nrows,ncols) mask.
        Args:
            M: A numpy boolean array of shape (nrows,ncols).
            georef: The GDAL style georefence of the input mask.
        Returns:
            A numpy 1d boolean mask.
        """
        ac=((self.xy-(georef[0],georef[3]))/(georef[1],georef[5])).astype(np.int32)
        N=np.logical_and(ac>=(0,0),ac<(M.shape[1],M.shape[0])).all(axis=1)
        ac=ac[N]
        MM=np.zeros((self.xy.shape[0],),dtype=np.bool)
        MM[N]=M[ac[:,1],ac[:,0]]
        return MM
    def cut_to_grid_mask(self,M,georef):
        """
        Cut to the which points lie within a (nrows,ncols) mask.
        Args:
            M: A numpy boolean array of shape (nrows,ncols).
            georef: The GDAL style georefence of the input mask.
        Returns:
            A new Pontcloud object.
        """
        MM=self.get_grid_mask(M,georef)
        return self.cut(MM)
    def cut_to_class(self,c,exclude=False):
        """
        Cut the pointcloud to points of a specific class.
        Args:
            c: class (integer) or iterable of integers.
            exclude: boolean indicating whether to use c as an exclusive list (cut to the complement).
        Returns:
            A new Pontcloud object.
        Raises:
            ValueError: if class attribute is not set.
        """
        #will now accept a list or another iterable...
        if self.c is None:
            raise ValueError("Class attribute not set.")
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
        
    def cut_to_return_number(self,rn):
        """
        Cut to points with return number rn (must have this attribute).
        Args:
            rn: return number to cut to.
        Returns:
            New Pointcloud object.
        Raises:
            ValueError: if no return numbers stored.
        """
        if self.rn is None:
            raise ValueError("Return number attribute not set.")
        I=(self.rn==rn)
        return self.cut(I)
       
    def cut_to_z_interval(self,zmin,zmax):
        """
        Cut the pointcloud to points in a z interval.
        Args:
            zmin: minimum z
            zmax: maximum z
        Returns:
            New Pointcloud object
        """
        I=np.logical_and((self.z>=zmin),(self.z<=zmax))
        return self.cut(I) 
    def cut_to_strip(self,id):
        """
        Cut the pointcloud to the points with a specific point source id.
        Args:
            id: The point source (strip) id to cut to.
        Returns:
            New Pointcloud object
        Raises:
            ValueError: If point source id attribute is not set.
        """
        if self.pid is None:
            raise ValueError("Point source id attribute not set")
        I=(self.pid==id)
        return self.cut(I)
    def triangulate(self):
        """
        Triangulate the pointcloud. Will do nothing if triangulation is already calculated.
        Raises:
            ValueError: If not at least 3 points in pointcloud
        """
        if self.triangulation is None:
            if self.xy.shape[0]>2:
                self.triangulation=triangle.Triangulation(self.xy)
            else:
                raise ValueError("Less than 3 points - unable to triangulate.")
    def set_validity_mask(self,mask):
        """
        Explicitely set a triangle validity mask.
        Args:
            mask: A boolean numpy array of size the number of triangles.
        Raises:
            ValueError: If triangulation not created or mask of inproper shape.
        """
        if self.triangulation is None:
            raise ValueError("Triangulation not created yet!")
        if mask.shape[0]!=self.triangulation.ntrig:
            raise ValueError("Invalid size of triangle validity mask.")
        self.triangle_validity_mask=mask
    def clear_validity_mask(self):
        """Clear the triangle validity mask (set it to None)"""
        self.triangle_validity_mask=None
    def calculate_validity_mask(self,max_angle=45,tol_xy=2,tol_z=1):
        """
        Calculate a triangle validity mask from geometry constrains.
        Args:
            max_angle: maximal angle/slope in degrees.
            tol_xy: maximal size of xy bounding box.
            tol_z: maximal size of z bounding box.
        """
        tanv2=np.tan(max_angle*np.pi/180.0)**2 #tanv squared
        geom=self.get_triangle_geometry()
        self.triangle_validity_mask=(geom<(tanv2,tol_xy,tol_z)).all(axis=1)
    def get_validity_mask(self):
        #just return the validity mask
        return self.triangle_validity_mask
    def get_grid(self,ncols=None,nrows=None,x1=None,x2=None,y1=None,y2=None,cx=None,cy=None,nd_val=-999,crop=0,method="triangulation"):
        """
        Grid (an attribute of) the pointcloud.
        Will calculate grid size and georeference from supplied input (or pointcloud extent).
        Args:
            ncols: number of columns.
            nrows: number of rows.
            x1: left pixel corner/edge (GDAL style).
            x2: right pixel corner/edge (GDAL style).
            y1: lower pixel corner/edge (GDAL style).
            y2: upper pixel corner/edge (GDAL style).
            cx: horisontal cell size.
            cy: vertical cell size.
            nd_val: grid no data value.
            crop: if calculating grid extent from pointcloud extent, crop the extent by this amount (should not be needed).
            method: One of the supported method/attribute names - triangulation,return_triangles,density,class,pid.
        Returns:
            A grid.Grid object and a grid.Grid object with triangle sizes if 'return_triangles' is specified.
        Raises:
            ValueError: If unable to calculate grid size or location from supplied input or using triangulation and triangulation not calculated or supplied with invalid method name.
        """
        #xl = left 'corner' of "pixel", not center.
        #yu= upper 'corner', not center.
        #returns grid and gdal style georeference...
        
        #The design here is not so nice. Should be possible to clean up a bit without disturbing too many tests.
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
                raise ValueError("Create a triangulation first...")
            g=self.triangulation.make_grid(self.z,ncols,nrows,x1,cx,y2,cy,nd_val,return_triangles=False)
            return grid.Grid(g,geo_ref,nd_val)
        elif method=="return_triangles":
            if self.triangulation is None:
                raise ValueError("Create a triangulation first...")
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
        """
        Find the (valid) containing triangles for an array of points.
        Args:
            xy_in: Numpy array of points ( shape (n,2), dtype float64)
            mask: optional triangle validity mask.
        Returns:
            Numpy array of triangle indices where -1 signals no (valid) triangle.
        """
        if self.triangulation is None:
            raise Exception("Create a triangulation first...")
        xy_in=point_factory(xy_in)
        #-2 indices signals outside triangulation, -1 signals invalid, else valid
        return self.triangulation.find_triangles(xy_in,mask)
        
    def find_appropriate_triangles(self,xy_in,mask=None):
        """
        Find the (valid) containing triangles for an array of points. Either the internal triangle validity mask must be set or a mask must be supplied in call.
        Args:
            xy_in: Numpy array of points ( shape (n,2), dtype float64)
            mask: Optional triangle validity mask. Will use internal triangle_validity_mask if not supplied here.
        Returns:
            Numpy array of triangle indices where -1 signals no (valid) triangle.
        Raises:
            ValueError: If triangle validty mask not available.
        """
        if mask is None:
            mask=self.triangle_validity_mask
        if mask is None:
            raise ValueError("This method needs a triangle validity mask.")
        return self.find_triangles(xy_in,mask)
    
    def get_points_in_triangulation(self,xy_in):
        #Not really used. Cut input xy to the points that lie inside the triangulation.
        #Can be used to implement a point in polygon algorithm!
        I=self.find_triangles(xy_in)
        return xy_in[I>=0]
        
    def get_points_in_valid_triangles(self,xy_in,mask=None):
        #Not really used. Cut input xy to the points that lie inside valid triangules.
        #Can be used to implement a point in polygon algorithm!
        I=self.find_appropriate_triangles(xy_in,mask)
        return xy_in[I>=0]
    
    def get_boundary_vertices(self,M_t,M_p):
        #Experimental and not really used.
        #Find the vertices which are marked by M_p and inside triangles marked by M_t
        M_out=array_geometry.get_boundary_vertices(M_t,M_p,self.triangulation.vertices)
        return M_out
        
    def interpolate(self,xy_in,nd_val=-999,mask=None):
        """
        TIN interpolate values in input points.
        Args:
            xy_in: The input points (anything that is convertable to a numpy (n,2) float64 array).
            nd_val: No data value for points not in any (valid) triangle.
            mask: Optional triangle validity mask.
        Returns:
            1d numpy array of interpolated values.
        Raises:
            ValueError: If triangulation not created.
        """
        if self.triangulation is None:
            raise ValueError("Create a triangulation first...")
        xy_in=point_factory(xy_in)
        return self.triangulation.interpolate(self.z,xy_in,nd_val,mask)
    #Interpolates points in valid triangles
    def controlled_interpolation(self,xy_in,mask=None,nd_val=-999):
        """
        TIN interpolate values in input points using only valid triangles.
        Args:
            xy_in: The input points (anything that is convertable to a numpy (n,2) float64 array).
            nd_val: No data value for points not in any (valid) triangle.
            mask: Optional triangle validity mask. Will use internal triangle_validity_mask if  mask not supplied in call.
        Returns:
            1d numpy array of interpolated values.
        Raises:
            ValueError: If triangulation not created or mask not available.
        """
        if mask is None:
            mask=self.triangle_validity_mask
        if mask is None:
            raise ValueError("This method needs a triangle validity mask.")
        return self.interpolate(xy_in,nd_val,mask)
        
    def get_triangle_geometry(self):
        """
        Calculate the triangle geometry as an array with rows: (tanv2_i,bb_xy_i,bb_z_i). 
        Here tanv2 is the squared tangent of the slope angle, bb_xy is the maximal edge of the planar bounding box, and bb_z_i the size of the vertical bounding box.
        Returns:
            Numpy array of shape (n,3) containing the geometry numbers for each triangle in the triangulation.
        Raises:
            ValueError: If triangulation not created.
        """
        if self.triangulation is None:
            raise ValueError("Create a triangulation first...")
        return array_geometry.get_triangle_geometry(self.xy,self.z,self.triangulation.vertices,self.triangulation.ntrig)
    
    def warp(self,sys_in,sys_out):
        pass #TODO - use TrLib
    
    def affine_transformation(self,R=None,T=None):
        """
        Modify points in place by an affine transformation xyz=R*xyz+T.
        Args:
            R: 3 times 3 array (scaling, rotation, etc.)
            T: Translation vector (dx,dy,dz)
        """
        #Wasting a bit of memory here to keep it simple!
        self.clear_derived_attrs()
        xyz=np.column_stack((self.xy,self.z))
        if R is not None:
            xyz=np.dot(R,xyz.T).T
        if T is not None:
            xyz+=T
        self.xy=xyz[:,:2].copy()
        self.z=xyz[:,2].copy()
    
    def affine_transformation_2d(self,R=None,T=None):
        """
        Modify xy points in place by a 2d affine transformation xy=R*xy+T.
        Args:
            R: 2 times 2 array (scaling, rotation, etc.)
            T: Translation vector (dx,dy)
        """
        self.clear_derived_attrs()
        if R is not None:
            self.xy=(np.dot(R,self.xy.T).T).copy()
        if T is not None:
            self.xy+=T
       
    def toE(self,geoid):
        """
        Warp to ellipsoidal heights. Modify z 'in place' by adding geoid height.
        Args:
            geoid: A geoid grid - grid.Grid instance.
        """
        #warp to ellipsoidal heights
        toE=geoid.interpolate(self.xy)
        assert((toE!=geoid.nd_val).all())
        self.z+=toE
        
    def toH(self,geoid):
        """
        Warp to orthometric heights. Modify z 'in place' by subtracting geoid height.
        Args:
            geoid: A geoid grid - grid.Grid instance.
        """
        #warp to orthometric heights. z bounds not stored, so no need to recalculate.
        toE=geoid.interpolate(self.xy)
        assert((toE!=geoid.nd_val).all())
        self.z-=toE
        
    def set_class(self,c):
        """Explicitely set the class attribute to be c for all points."""
        self.c=np.ones(self.z.shape,dtype=np.int32)*c
    #dump methods
    def dump_csv(self,f,callback=None):
        """
        Dump the pointcloud as a csv file. Will dump available attributes, except for return_number.
        Args:
            f: A file pointer
            callback: An optional method to use for logging.
        """
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
        """Just dump the xyz attrs of a pointcloud as a whitespace separated text file."""
        xyz=np.column_stack((self.xy,self.z))
        np.savetxt(path,xyz)
    def dump_npy(self,path):
        xyz=np.column_stack((self.xy,self.z))
        np.save(path,xyz)
    def dump_bin(self,path):
        """
        Dump the pointcloud as a (platform dependent) binary file. Each entry will consists of x,y,z,class,pid as doubles.
        Must have classification and point source id attributes.
        Args:
            path: Filename to dump to.
        """
        assert(self.c is not None)
        assert(self.pid is not None)
        xyzcp=np.column_stack((self.xy,self.z,self.c.astype(np.float64),self.pid.astype(np.float64))).astype(np.float64)
        xyzcp.tofile(path)
    def sort_spatially(self,cs,shape=None,xy_ul=None):
        """
        Primitive spatial sorting by creating a 'virtual' 2D grid covering the pointcloud and thus a 1D index by consecutive c style numbering of cells.
        Keep track of 'slices' of the pointcloud within each 'virtual' cell.
        As the pointcloud is reordered all derived attributes will be cleared.
        Returns:
            A reference to self.
        """
         
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
        """
        Clear derived attributes which will change after an in place modification, like an extension.
        """
        #Clears attrs which become invalid by an extentsion or sorting
        self.triangulation=None
        self.index_header=None
        self.spatial_index=None
        self.bbox=None
        self.triangle_validity_mask=None
    #Filterering methods below...
    def validate_filter_args(self,rad):
        #internal utility - just validate a filter radius against the internal spatial index.
        if self.spatial_index is None:
            raise Exception("Build a spatial index first!")
        if rad>self.index_header[4]:
            raise Warning("Filter radius larger than cell size of spatial index will not catch all points!")
    def min_filter(self, filter_rad,xy=None, nd_val=-9999):
        """
        Calculate minumum filter of z along self.xy or a supplied set of input points. Useful for gridding.
        Args:
            filter_rad: The radius of the filter. Should not be larger than cell size in spatial index (for now).
            xy: Optional list of input points to filter along. Will use self.xy if not supplied.
        Returns:
            1D array of filtered values.
        """
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_min_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def mean_filter(self, filter_rad, xy=None, nd_val=-9999):
        """
        Calculate mean filter of z along self.xy or a supplied set of input points. Useful for gridding.
        Args:
            filter_rad: The radius of the filter. Should not be larger than cell size in spatial index (for now).
            xy: Optional list of input points to filter along. Will use self.xy if not supplied.
        Returns:
            1D array of filtered values.
        """
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_mean_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def max_filter(self,filter_rad,xy=None,nd_val=-9999):
        """
        Calculate maximum filter of z along self.xy or a supplied set of input points. Useful for gridding.
        Args:
            filter_rad: The radius of the filter. Should not be larger than cell size in spatial index (for now).
            xy: Optional list of input points to filter along. Will use self.xy if not supplied.
        Returns:
            1D array of filtered values.
        """
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_min_filter(xy,self.xy,-self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return -z_out
    def median_filter(self, filter_rad, xy=None,nd_val=-9999):
        """
        Calculate median filter of z along self.xy or a supplied set of input points. Useful for gridding.
        Args:
            filter_rad: The radius of the filter. Should not be larger than cell size in spatial index (for now).
            xy: Optional list of input points to filter along. Will use self.xy if not supplied.
        Returns:
            1D array of filtered values.
        """
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_median_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def var_filter(self, filter_rad, xy=None, nd_val=-9999):
        """
        Calculate variance filter of z along self.xy or a supplied set of input points. Useful for gridding.
        Args:
            filter_rad: The radius of the filter. Should not be larger than cell size in spatial index (for now).
            xy: Optional list of input points to filter along. Will use self.xy if not supplied.
        Returns:
            1D array of filtered values.
        """
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_var_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def distance_filter(self, filter_rad,xy=None,nd_val=9999):
        """
        Calculate point distance filter along self.xy or a supplied set of input points (which should really be supplied for this to make sense). Useful for gridding.
        Args:
            filter_rad: The radius of the filter. Should not be larger than cell size in spatial index (for now).
            xy: Optional list of input points to filter along. Supply this or get a lot of zeros!
        Returns:
            1D array of filtered values.
        """
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_distance_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def density_filter(self, filter_rad, xy=None):
        """
        Calculate point density filter along self.xy or a supplied set of input points. Useful for gridding.
        Args:
            filter_rad: The radius of the filter. Should not be larger than cell size in spatial index (for now).
            xy: Optional list of input points to filter along. Will use self.xy if not supplied.
        Returns:
            1D array of filtered values.
        """
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_density_filter(xy,self.xy,self.z,z_out,filter_rad,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def idw_filter(self,filter_rad,xy=None,nd_val=-9999):
        """
        Calculate inverse distance weighted z values along self.xy or a supplied set of input points. Useful for gridding.
        Args:
            filter_rad: The radius of the filter. Should not be larger than cell size in spatial index (for now).
            xy: Optional list of input points to filter along. Will use self.xy if not supplied.
        Returns:
            1D array of filtered values.
        """
        self.validate_filter_args(filter_rad)
        if xy is None:
            xy=self.xy
        z_out=np.zeros((xy.shape[0],),dtype=np.float64)
        array_geometry.lib.pc_idw_filter(xy,self.xy,self.z,z_out,filter_rad,nd_val,self.spatial_index,self.index_header,xy.shape[0])
        return z_out
    def spike_filter(self, filter_rad,tanv2,zlim=0.2):
        """
        Calculate spike indicators (0 or 1) for each point . In order to be a spike there must be at least one other point within filter rad in each quadrant which satisfies:
        -- slope_angle large and dz large.
        See c implementation in array_geometry.c.
        Args:
            filter_rad: The radius of the filter. Should not be larger than cell size in spatial index (for now).
            tanv2: Tangent squared of slope angle (dy/dx)**2 parameter for spike check (lower limit).
            zlim: dz paramter for spike check (lower limit) 
        Returns:
            1D array of spike indications (0 or 1).
        """
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



    
        
        
