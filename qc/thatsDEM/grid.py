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
######################################
##  Grid class below  - just a numpy array and some metadata + some usefull methods             
####################################
import numpy as np
import os
from osgeo import gdal
import ctypes
try:
    import scipy.ndimage as image
except:
    HAS_NDIMAGE=False
else:
    HAS_NDIMAGE=True
LIBDIR=os.path.realpath(os.path.join(os.path.dirname(__file__),"../lib"))
LIBNAME="libgrid"
XY_TYPE=np.ctypeslib.ndpointer(dtype=np.float64,flags=['C','O','A','W'])
GRID_TYPE=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags=['C','O','A','W'])
Z_TYPE=np.ctypeslib.ndpointer(dtype=np.float64,ndim=1,flags=['C','O','A','W'])
UINT32_TYPE=np.ctypeslib.ndpointer(dtype=np.uint32,ndim=1,flags=['C','O','A','W'])
INT32_GRID_TYPE=np.ctypeslib.ndpointer(dtype=np.int32,ndim=2,flags=['C','O','A','W'])
INT32_TYPE=np.ctypeslib.ndpointer(dtype=np.int32,ndim=1,flags=['C','O','A','W'])
LP_CDOUBLE=ctypes.POINTER(ctypes.c_double)
GEO_REF_ARRAY=ctypes.c_double*4
lib=np.ctypeslib.load_library(LIBNAME, LIBDIR)
#void wrap_bilin(double *grid, double *xy, double *out, double *geo_ref, double nd_val, int nrows, int ncols, int npoints)
lib.wrap_bilin.argtypes=[GRID_TYPE,XY_TYPE,Z_TYPE,LP_CDOUBLE,ctypes.c_double,ctypes.c_int,ctypes.c_int,ctypes.c_int]
lib.wrap_bilin.restype=None
#DLL_EXPORT void resample_grid(double *grid, double *out, double *geo_ref, double *geo_ref_out, double nd_val, int nrows, int ncols, int nrows_out, int ncols_out)
lib.resample_grid.argtypes=[GRID_TYPE,GRID_TYPE,LP_CDOUBLE,LP_CDOUBLE,ctypes.c_double,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int]
lib.resample_grid.restype=None
# void grid_most_frequent_value(int *sorted_indices, int *values, int *out, int vmin,int vmax,int nd_val, int n)
lib.grid_most_frequent_value.argtypes=[INT32_TYPE,INT32_TYPE,INT32_GRID_TYPE,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int]
lib.grid_most_frequent_value.restype=None

#If there's no natural nodata value connected to the grid, it is up to the user to supply a nd_val which is not a regular grid value.
#If supplied geo_ref should be a 'sequence' of len 4 (duck typing here...)

#COMPRESSION OPTIONS FOR SAVING GRIDS AS GTIFF
DCO=["TILED=YES","COMPRESS=LZW"]

#Kernels for hillshading
ZT_KERNEL=np.array([[0,0,0],[-1,0,1],[0,0,0]],dtype=np.float32) #Zevenberg-Thorne
H_KERNEL=np.array([[-1,0,1],[-2,0,2],[-1,0,1]],dtype=np.float32) #Horn

def fromGDAL(path,upcast=False):
    """
    Open a 1-band grid from a GDAL datasource.
    Args:
        path: GDAL connection string
        upcast: bool, indicates whether to upcast dtype to float64
    Returns:
        grid.Grid object
    """
    ds=gdal.Open(path)
    a=ds.ReadAsArray()
    if upcast:
        a=a.astype(np.float64)
    geo_ref=ds.GetGeoTransform()
    srs=ds.GetProjection()
    nd_val=ds.GetRasterBand(1).GetNoDataValue()
    ds=None
    return Grid(a,geo_ref,nd_val,srs=srs)

def bilinear_interpolation(grid,xy,nd_val,geo_ref=None):
    """
    Perform bilinear interpolation in a grid. Will call a c-library extension.
    Args:
        grid: numpy array (of type numpy.float64)
        xy: numpy array of shape (n,2) (and dtype numpy.float64). The points to interpolate values for.
        nd_val: float, output no data value.
        geo_ref: iterable of floats: (xulcenter, hor_cellsize, yulcenter, vert_cellsize). NOT GDAL style georeference. If None xy is assumed to be in array coordinates.
    Returns:
        A 1d, float64 numpy array containing the interpolated values.
    """
        
    if geo_ref is not None:
        if len(geo_ref)!=4:
            raise Exception("Geo reference should be sequence of len 4, xulcenter, cx, yulcenter, cy")
        geo_ref=GEO_REF_ARRAY(*geo_ref)
    p_geo_ref=ctypes.cast(geo_ref,LP_CDOUBLE)  #null or pointer to geo_ref
    grid=np.require(grid,dtype=np.float64,requirements=['A', 'O', 'C','W'])
    xy=np.require(xy,dtype=np.float64,requirements=['A', 'O', 'C','W'])
    out=np.zeros((xy.shape[0],),dtype=np.float64)
    lib.wrap_bilin(grid,xy,out,p_geo_ref,nd_val,grid.shape[0],grid.shape[1],xy.shape[0])
    return out

def resample_grid(grid,nd_val,geo_ref_in,geo_ref_out,ncols_out,nrows_out):
    """
    Resample (upsample / downsample) a grid using bilinear interpolation.
    Args:
        grid: numpy input 2d array (float64)
        nd_val: output no data value
        georef: iterable of floats: (xulcenter, hor_cellsize, yulcenter, vert_cellsize). NOT GDAL style georeference. 
        ncols_out: Number of columns in output.
        nrows_out: Number of rows in output.
    Returns:
        output numpy 2d array (float64)
    """
    if len(geo_ref_in)!=4 or len(geo_ref_out)!=4:
        raise Exception("Geo reference should be sequence of len 4, xulcenter, cx, yulcenter, cy")
    geo_ref_in=GEO_REF_ARRAY(*geo_ref_in)
    geo_ref_out=GEO_REF_ARRAY(*geo_ref_out)
    p_geo_ref_in=ctypes.cast(geo_ref_in,LP_CDOUBLE)  #null or pointer to geo_ref
    p_geo_ref_out=ctypes.cast(geo_ref_out,LP_CDOUBLE)  #null or pointer to geo_ref
    grid=np.require(grid,dtype=np.float64,requirements=['A', 'O', 'C','W'])
    out=np.empty((nrows_out,ncols_out),dtype=np.float64)
    lib.resample_grid(grid,out,p_geo_ref_in,p_geo_ref_out,nd_val,grid.shape[0],grid.shape[1],nrows_out,ncols_out)
    return out


    


#slow, but flexible method designed to calc. some algebraic quantity of q's within every single cell
def make_grid(xy,q,ncols, nrows, georef, nd_val=-9999, method=np.mean,dtype=np.float32): #gdal-style georef
    """
    Apply a function on scattered data (xy) to produce a regular grid. Will apply the supplied method on the points that fall within each output cell.
    Args:
        xy: numpy array of shape (n,2).
        q: 1d numpy array. The value to 'grid'.
        ncols: Number of columns in output.
        nrows: Number of rows in output.
        georef: GDAL style georeference (list / tuple containing 6 floats).
        nd_val: Output no data value.
        method: The method to apply to the points that are contained in each cell.
        dtype: Output numpy data type.
    Returns:
        2d numpy array of shape (nrows,ncols).
    """
    out=np.ones((nrows,ncols),dtype=dtype)*nd_val
    arr_coords=((xy-(georef[0],georef[3]))/(georef[1],georef[5])).astype(np.int32)
    M=np.logical_and(arr_coords[:,0]>=0, arr_coords[:,0]<ncols)
    M&=np.logical_and(arr_coords[:,1]>=0,arr_coords[:,1]<nrows)
    arr_coords=arr_coords[M]
    q=q[M]
    #create flattened index
    B=arr_coords[:,1]*ncols+arr_coords[:,0]
    #now sort array
    I=np.argsort(B)
    arr_coords=arr_coords[I]
    q=q[I]
    #and finally loop through pts just one more time...
    box_index=arr_coords[0,1]*ncols+arr_coords[0,0]
    i0=0
    row=arr_coords[0,1]
    col=arr_coords[0,0]
    for i in xrange(arr_coords.shape[0]):
        b=arr_coords[i,1]*ncols+arr_coords[i,0]
        if (b>box_index):
            #set the current cell
            out[row,col]=method(q[i0:i])
            #set data for the next cell
            i0=i
            box_index=b
            row=arr_coords[i,1]
            col=arr_coords[i,0]
    #set the final cell - corresponding to largest box_index
    assert ((arr_coords[i0]==arr_coords[-1]).all())
    final_val=method(q[i0:])
    out[row,col]=final_val
    return Grid(out,georef,nd_val)

def grid_most_frequent_value(xy,q,ncols,nrows,georef,v1=None,v2=None,nd_val=-9999):
    # void grid_most_frequent_value(int *sorted_indices, int *values, int *out, int vmin,int vmax,int nd_val, int n)
    out=np.ones((nrows,ncols),dtype=np.int32)*nd_val
    arr_coords=((xy-(georef[0],georef[3]))/(georef[1],georef[5])).astype(np.int32)
    M=np.logical_and(arr_coords[:,0]>=0, arr_coords[:,0]<ncols)
    M&=np.logical_and(arr_coords[:,1]>=0,arr_coords[:,1]<nrows)
    arr_coords=arr_coords[M]
    q=q[M]
    #create flattened index
    B=arr_coords[:,1]*ncols+arr_coords[:,0]
    del arr_coords
    #now sort array
    I=np.argsort(B)
    B=B[I]
    q=q[I]
    if v1 is None:
        v1=q.min()
    if v2 is None:
        v2=q.max()
    lib.grid_most_frequent_value(B,q,out,v1,v2,nd_val,B.shape[0])
    return Grid(out,georef,nd_val)


def user2array(georef,xy):
    return ((xy-(georef[0],georef[3]))/(georef[1],georef[5])).astype(np.int32)

def grid_extent(geo_ref,shape): #use a GDAL-style georef and a numpy style shape
    x1=geo_ref[0]
    y2=geo_ref[3]
    x2=x1+shape[1]*geo_ref[1]
    y1=y2+shape[0]*geo_ref[5]
    return (x1,y1,x2,y2)

def intersect_grid_extents(georef1,shape1,georef2,shape2):
    #Will calculate the pixel extent (slices) of the intersection of two grid extents in each pixel coord. set
    #Avoid rounding issues
    if (georef1[1]!=georef2[1] or georef1[5]!=georef2[5]): #TODO check alignment
        raise ValueError("Must have same cell size and 'alignment'")
    extent1=np.array(grid_extent(georef1,shape1))
    extent2=np.array(grid_extent(georef2,shape2))
    #calculate intersection
    x1,y1=np.maximum(extent1[:2],extent2[:2])
    x2,y2=np.minimum(extent1[2:],extent2[2:])
    #print x1,y1,x2,y2
    #print extent1
    #print extent2
    if (x1>=x2 or y1>=y2):
        return None,None
    ullr=np.array(((x1,y2),(x2,y1)),dtype=np.float64)
    ullr+=(georef1[1]*0.5,georef1[5]*0.5) #avoid rounding
    slice1=user2array(georef1,ullr)
    slice2=user2array(georef2,ullr)
    #will return two (row_slice,col_slices)
    rs1=slice(slice1[0,1],slice1[1,1])
    rs2=slice(slice2[0,1],slice2[1,1])
    cs1=slice(slice1[0,0],slice1[1,0])
    cs2=slice(slice2[0,0],slice2[1,0])
    return (rs1,cs1),(rs2,cs2)



class Grid(object):
    """
    Grid abstraction class.
    Contains a numpy array and metadata like geo reference.
    """
    def __init__(self,arr,geo_ref,nd_val=None,srs=None):
        self.grid=arr
        self.geo_ref=np.array(geo_ref)
        self.nd_val=nd_val
        self.srs=srs
        #and then define some useful methods...
    @property
    def shape(self):
        return self.grid.shape
    @property
    def dtype(self):
        return self.grid.dtype
    def expand_vert(self,pos,buf):
        assert(self.nd_val is not None)
        band=np.ones((buf,self.grid.shape[1]),dtype=self.grid.dtype)*self.nd_val
        if pos<0: #top
           self.grid=np.vstack((band,self.grid))
           self.geo_ref[3]-=self.geo_ref[5]*buf
        elif pos>0: #bottom
            self.grid=np.vstack((self.grid,band))
        return self
    def expand_hor(self,pos,buf):
        assert(self.nd_val is not None)
        band=np.ones((self.grid.shape[0],buf),dtype=self.grid.dtype)*self.nd_val
        if pos<0: #left
           self.grid=np.hstack((band,self.grid))
           self.geo_ref[0]-=self.geo_ref[1]*buf
        elif pos>0: #right
            self.grid=np.hstack((self.grid,band))
        return self
    #shrink methods should return views - so beware... perhaps use resize...
    def shrink_vert(self,pos,buf):
        """
        Shrink the grid vertically by buf pixels. If pos is 1 shrink from top, if pos is -1 shrink at bottom.
        Beware: The internal grid will now be a view.
        """
        assert(self.grid.shape[0]>buf)
        if pos<0: #top
            self.grid=self.grid[buf:,:]
            self.geo_ref[3]+=self.geo_ref[5]*buf
        elif pos>0: #bottom
             self.grid=self.grid[:-buf,:]
        return self
    def shrink_hor(self,pos,buf):
        """
        Shrink the grid horisontally by buf pixels. If pos is 1 shrink from right, if pos is -1 shrink from left.
        Beware: The internal grid will now be a view.
        """
        assert(self.grid.shape[1]>buf)
        if pos<0: #left
            self.grid=self.grid[:,buf:]
            self.geo_ref[0]+=self.geo_ref[1]*buf
        elif pos>0: #right
             self.grid=self.grid[:,:-buf]
        return self
    def shrink(self,shrink,copy=False):
        #Will return a view unless copy=True, be carefull! Can be extended to handle more general slices...
        assert(min(self.grid.shape)>2*shrink)
        if shrink<=0:
            return self
        G=self.grid[shrink:-shrink,shrink:-shrink]
        if copy:
            G=G.copy()
        geo_ref=list(self.geo_ref[:])
        geo_ref[0]+=shrink*self.geo_ref[1]
        geo_ref[3]+=shrink*self.geo_ref[5]
        return Grid(G,geo_ref,self.nd_val)
    def interpolate(self,xy,nd_val=None):
        #If the grid does not have a nd_val, the user must supply one here...
        if self.nd_val is None:
            if nd_val is None:
                raise Exception("No data value not supplied...")
        else:
            if nd_val is not None:
                raise Warning("User supplied nd-val not used as grid already have one...")
            nd_val=self.nd_val
        cx=self.geo_ref[1]
        cy=self.geo_ref[5]
        cell_georef=[self.geo_ref[0]+0.5*cx,cx,self.geo_ref[3]+0.5*cy,-cy]  #geo_ref used in interpolation ('corner' coordinates...)
        return bilinear_interpolation(self.grid,xy,nd_val,cell_georef)
    def save(self,fname,format="GTiff",dco=[],colortable=None, srs=None):
        #TODO: map numpy types to gdal types better - done internally in gdal I think...
        if self.grid.dtype==np.float32:
            dtype=gdal.GDT_Float32
        elif self.grid.dtype==np.float64:
            dtype=gdal.GDT_Float64
        elif self.grid.dtype==np.int32:
            dtype=gdal.GDT_Int32
        elif self.grid.dtype==np.bool or self.grid.dtype==np.uint8:
            dtype=gdal.GDT_Byte
        else:
            return False #TODO....
        driver=gdal.GetDriverByName(format)
        assert(driver is not None)
        if os.path.exists(fname):
            try:
                driver.Delete(fname)
            except Exception, msg:
                print msg
            else:
                print("Overwriting %s..." %fname)	
        else:
            print("Saving %s..."%fname)
        if len(dco)>0:
            dst_ds=driver.Create(fname,self.grid.shape[1],self.grid.shape[0],1,dtype,options=dco)
        else:
            dst_ds=driver.Create(fname,self.grid.shape[1],self.grid.shape[0],1,dtype)
        dst_ds.SetGeoTransform(self.geo_ref)
        if srs is None: #will override self.srs which is default if set
            srs=self.srs
        if srs is not None:
            dst_ds.SetProjection(srs)
        band=dst_ds.GetRasterBand(1)
        if self.nd_val is not None:
            band.SetNoDataValue(self.nd_val)
        band.WriteArray(self.grid)
        dst_ds=None
        return True
    
    def get_bounds(self):
        return grid_extent(self.geo_ref,self.grid.shape)
        
    def correlate(self,other):
        pass #TODO
    
    def get_hillshade(self,azimuth=315,height=45,z_factor=1.0,method=0): #method 0 is Horn - smoother, otherwise Zevenberg-Thorne - faster.
        #requires scipy.ndimage
        #light should be the direction to the sun
        if not HAS_NDIMAGE:
            raise ValueError("This method requires scipy.ndimage")
        ang=np.radians(360-azimuth+90)
        h_rad=np.radians(height)
        light=np.array((np.cos(ang)*np.cos(h_rad),np.sin(ang)*np.cos(h_rad),np.sin(h_rad)))
        light=light/(np.sqrt(light.dot(light))) #normalise
        if method==0:
            kernel=H_KERNEL
            k_factor=8
        else:
            kernel=ZT_KERNEL
            k_factor=2
        scale_x=z_factor/(self.geo_ref[1]*k_factor) #scale down
        scale_y=z_factor/(self.geo_ref[5]*k_factor)
        dx=image.filters.correlate(self.grid,kernel)*scale_x
        dy=image.filters.correlate(self.grid,kernel.T)*scale_y #taking care of revered axis since cy<0
        #The normal vector looks like (-dx,-dy,1) - in array coords: (-dx,dy,1)
        X=np.sqrt(dx**2+dy**2+1) #the norm of the normal 
        #calculate the dot product and normalise - should be in range -1 to 1 - less than zero means black, which here should translate to the value 1 as a ubyte.
        X=(-dx*light[0]-dy*light[1]+light[2])/X
        print X.min(),X.max()
        X[X<0]=0 #dark pixels should have value 1
        X=X*254+1
        #should not happen
        X[X>255]=255 #there should be none
        #end should not happen
        M=(self.grid==self.nd_val)
        if M.any():
            T=((np.fabs(kernel)+np.fabs(kernel.T))>0)
            M=image.morphology.binary_dilation(M,T)
        X[M]=0
        X=X.astype(np.uint8)
        return Grid(X,self.geo_ref,nd_val=0,srs=self.srs) #cast shadow
    