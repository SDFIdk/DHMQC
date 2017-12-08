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
import sys
import os
import ctypes
import numpy as np
from osgeo import ogr

ogr.UseExceptions()

LIBDIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "lib"))
LIBNAME = "libfgeom"
XY_TYPE = np.ctypeslib.ndpointer(dtype=np.float64, flags=['C', 'O', 'A', 'W'])
GRID_TYPE = np.ctypeslib.ndpointer(dtype=np.float64, ndim=2, flags=['C', 'O', 'A', 'W'])
GRID32_TYPE = np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags=['C', 'O', 'A', 'W'])
Z_TYPE = np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags=['C', 'O', 'A', 'W'])
MASK_TYPE = np.ctypeslib.ndpointer(dtype=np.bool, ndim=1, flags=['C', 'O', 'A', 'W'])
MASK2D_TYPE = np.ctypeslib.ndpointer(dtype=np.bool, ndim=2, flags=['C', 'O', 'A', 'W'])
UINT32_TYPE = np.ctypeslib.ndpointer(dtype=np.uint32, ndim=1, flags=['C', 'O', 'A'])
HMAP_TYPE = np.ctypeslib.ndpointer(dtype=np.uint32, ndim=2, flags=['C', 'O', 'A'])
UINT8_VOXELS = np.ctypeslib.ndpointer(dtype=np.uint8, ndim=3, flags=['C', 'O', 'A', 'W'])
INT32_VOXELS = np.ctypeslib.ndpointer(dtype=np.int32, ndim=3, flags=['C', 'O', 'A', 'W'])
INT32_TYPE = np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags=['C', 'O', 'A', 'W'])
LP_CINT = ctypes.POINTER(ctypes.c_int)
LP_CCHAR = ctypes.POINTER(ctypes.c_char)
lib = np.ctypeslib.load_library(LIBNAME, LIBDIR)
##############
# corresponds to
# array_geometry.h
##############
# void p_in_buf(double *p_in, char *mout, double *verts, unsigned long np, unsigned long nv, double d)
lib.p_in_buf.argtypes = [XY_TYPE, MASK_TYPE, XY_TYPE, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_double]
lib.p_in_buf.restype = None
lib.p_in_poly.argtypes = [XY_TYPE, MASK_TYPE, XY_TYPE, ctypes.c_uint, UINT32_TYPE, ctypes.c_uint]
lib.p_in_poly.restype = ctypes.c_int
lib.get_triangle_geometry.argtypes = [
    XY_TYPE, Z_TYPE, LP_CINT, np.ctypeslib.ndpointer(
        dtype=np.float32, ndim=2, flags=[
            'C', 'O', 'A', 'W']), ctypes.c_int]
lib.get_triangle_geometry.restype = None
lib.mark_bd_vertices.argtypes = [MASK_TYPE, MASK_TYPE, LP_CINT, MASK_TYPE, ctypes.c_int, ctypes.c_int]
lib.mark_bd_vertices.restype = None
# int fill_spatial_index(int *sorted_flat_indices, int *index, int npoints, int max_index)
lib.fill_spatial_index.argtypes = [INT32_TYPE, INT32_TYPE, ctypes.c_int, ctypes.c_int]
lib.fill_spatial_index.restype = ctypes.c_int
STD_FILTER_ARGS = [
    XY_TYPE,
    XY_TYPE,
    Z_TYPE,
    Z_TYPE,
    ctypes.c_double,
    ctypes.c_double,
    INT32_TYPE,
    XY_TYPE,
    ctypes.c_int]
lib.pc_min_filter.argtypes = STD_FILTER_ARGS
lib.pc_min_filter.restype = None
lib.pc_mean_filter.argtypes = STD_FILTER_ARGS
lib.pc_mean_filter.restype = None
lib.pc_idw_filter.argtypes = STD_FILTER_ARGS
lib.pc_idw_filter.restype = None
lib.pc_median_filter.argtypes = STD_FILTER_ARGS
lib.pc_median_filter.restype = None
lib.pc_var_filter.argtypes = STD_FILTER_ARGS
lib.pc_var_filter.restype = None
lib.pc_distance_filter.argtypes = STD_FILTER_ARGS
lib.pc_distance_filter.restype = None
lib.pc_density_filter.argtypes = [
    XY_TYPE,
    XY_TYPE,
    Z_TYPE,
    Z_TYPE,
    ctypes.c_double,
    INT32_TYPE,
    XY_TYPE,
    ctypes.c_int]
lib.pc_density_filter.restype = None
lib.pc_spike_filter.argtypes = [
    XY_TYPE,
    Z_TYPE,
    XY_TYPE,
    Z_TYPE,
    Z_TYPE,
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_double,
    INT32_TYPE,
    XY_TYPE,
    ctypes.c_int]
lib.pc_spike_filter.restype = None
# void pc_noise_filter(double *pc_xy, double *pc_z, double *z_out, double filter_rad, double zlim, double den_cut, int *spatial_index, double *header, int npoints);
# binning
# void moving_bins(double *z, int *nout, double rad, int n);
lib.moving_bins.argtypes = [Z_TYPE, INT32_TYPE, ctypes.c_double, ctypes.c_int]
lib.moving_bins.restype = None
# a triangle based filter
# void tri_filter_low(double *z, double *zout, int *tri, double cut_off, int ntri)
lib.tri_filter_low.argtypes = [Z_TYPE, Z_TYPE, LP_CINT, ctypes.c_double, ctypes.c_int]
lib.tri_filter_low.restype = None
# hmap filler
# void fill_it_up(unsigned char *out, unsigned int *hmap, int rows, int cols, int stacks);
lib.fill_it_up.argtypes = [UINT8_VOXELS, HMAP_TYPE] + [ctypes.c_int] * 3
lib.fill_it_up.restype = None
lib.find_floating_voxels.argtypes = [INT32_VOXELS, INT32_VOXELS] + [ctypes.c_int] * 4
lib.find_floating_voxels.restype = None
# int flood_cells(float *dem, float cut_off, char *mask, char *mask_out, int nrows, int ncols)
lib.flood_cells.argtypes = [GRID32_TYPE, ctypes.c_float, MASK2D_TYPE, MASK2D_TYPE] + [ctypes.c_int] * 2
lib.flood_cells.restype = ctypes.c_int
# void masked_mean_filter(float *dem, float *out, char *mask, int filter_rad, int nrows, int ncols)
lib.masked_mean_filter.argtypes = [GRID32_TYPE, GRID32_TYPE, MASK2D_TYPE] + [ctypes.c_int] * 3
lib.binary_fill_gaps.argtypes = [MASK2D_TYPE, MASK2D_TYPE, ctypes.c_int, ctypes.c_int]
lib.binary_fill_gaps.restype = None


def binary_fill_gaps(M):
    N = np.zeros_like(M)
    lib.binary_fill_gaps(M, N, M.shape[0], M.shape[1])
    return N


def moving_bins(z, rad):
    """
    Count points within a bin of size 2*rad around each point.
    Corresponds to a 'moving' histogram, or a 1d 'count filter'.
    """
    # Will sort input -- so no need to do that first...
    zs = np.sort(z).astype(np.float64)
    n_out = np.zeros(zs.shape, dtype=np.int32)
    lib.moving_bins(zs, n_out, rad, zs.shape[0])
    return zs, n_out


def tri_filter_low(z, tri, ntri, cut_off):
    """
    Triangulation based filtering of input z.
    Will test dz for each edge, and replace high point with low point if dz is larger than cut_off.
    Used to flatten steep triangles which connect e.g. a water point to a vegetation point on a tree
    """
    zout = np.copy(z)
    lib.tri_filter_low(z, zout, tri, cut_off, ntri)
    return zout


def masked_mean_filter(dem, mask, rad=2):
    """
    Mean filter of a dem, using only values within mask and changing only values within mask.
    """
    assert(mask.shape == dem.shape)
    assert(rad >= 1)
    out = np.copy(dem)
    lib.masked_mean_filter(dem, out, mask, rad, dem.shape[0], dem.shape[1])
    return out


def flood_cells(dem, cut_off, water_mask):
    # experimental 'downhill' expansion of water cells
    assert(water_mask.shape == dem.shape)
    out = np.copy(water_mask)
    n = lib.flood_cells(dem, cut_off, water_mask, out, dem.shape[0], dem.shape[1])
    return out, n


def ogrpoints2array(ogr_geoms):
    """
    Convert a list of OGR point geometries to a numpy array.
    Slow interface.
    """
    out = np.empty((len(ogr_geoms), 3), dtype=np.float64)
    for i in xrange(len(ogr_geoms)):
        out[i, :] = ogr_geoms[i].GetPoint()
    return out


def ogrmultipoint2array(ogr_geom, flatten=False):
    """
    Convert a OGR multipoint geometry to a numpy (2d or 3d) array.
    """
    t = ogr_geom.GetGeometryType()
    assert(t == ogr.wkbMultiPoint or t == ogr.wkbMultiPoint25D)
    ng = ogr_geom.GetGeometryCount()
    out = np.zeros((ng, 3), dtype=np.float64)
    for i in range(ng):
        out[i] = ogr_geom.GetGeometryRef(i).GetPoint()
    if flatten:
        out = out[:, 0:2].copy()
    return out


def ogrgeom2array(ogr_geom, flatten=True):
    """
    OGR geometry to numpy array dispatcher.
    Will just send the geometry to the appropriate converter based on geometry type.
    """
    t = ogr_geom.GetGeometryType()
    if t == ogr.wkbLineString or t == ogr.wkbLineString25D:
        return ogrline2array(ogr_geom, flatten)
    elif t == ogr.wkbPolygon or t == ogr.wkbPolygon25D:
        return ogrpoly2array(ogr_geom, flatten)
    elif t == ogr.wkbMultiPoint or t == ogr.wkbMultiPoint25D:
        return ogrmultipoint2array(ogr_geom, flatten)
    else:
        raise Exception("Unsupported geometry type: %s" % ogr_geom.GetGeometryName())


def ogrpoly2array(ogr_poly, flatten=True):
    """
    Convert a OGR polygon geometry to a list of numpy arrays.
    The first element will be the outer ring. Subsequent elements correpsond to the boundary of holes.
    Will not handle 'holes in holes'.
    """
    ng = ogr_poly.GetGeometryCount()
    rings = []
    for i in range(ng):
        ring = ogr_poly.GetGeometryRef(i)
        arr = np.asarray(ring.GetPoints())
        if flatten and arr.shape[1] > 2:
            arr = arr[:, 0:2].copy()
        rings.append(arr)
    return rings


def ogrline2array(ogr_line, flatten=True):
    """
    Convert a OGR linestring geometry to a numpy array (of vertices).
    """
    t = ogr_line.GetGeometryType()
    assert(t == ogr.wkbLineString or t == ogr.wkbLineString25D)
    pts = ogr_line.GetPoints()
    # for an incompatible geometry ogr returns None... but does not raise a python error...!
    if pts is None:
        if flatten:
            return np.empty((0, 2))
        else:
            return np.empty((0, 3))
    arr = np.asarray(pts)
    if flatten and arr.shape[1] > 2:
        arr = arr[:, 0:2].copy()
    return arr


def points_in_buffer(points, vertices, dist):
    """
    Calculate a mask indicating whether points lie within a distance (given by dist) of a line specified by the vertices arg.
    """
    out = np.empty((points.shape[0],), dtype=np.bool)  # its a byte, really
    lib.p_in_buf(points, out, vertices, points.shape[0], vertices.shape[0], dist)
    return out


def get_triangle_geometry(xy, z, triangles, n_triangles):
    """
    Calculate the geometry of each triangle in a triangulation as an array with rows: (tanv2_i,bb_xy_i,bb_z_i).
    Here tanv2 is the squared tangent of the slope angle, bb_xy is the maximal edge of the planar bounding box, and bb_z_i the size of the vertical bounding box.
    Args:
        xy: The vertices of the triangulation.
        z: The z values of the vertices.
        triangles: ctypes pointer to a c-contiguous int array of triangles, where each row contains the indices of the three vertices of a triangle.
        n_triangles: The number of triangles (rows in triangle array== size /3)
    Returns:
        Numpy array of shape (n,3) containing the geometry numbers for each triangle in the triangulation.
    """
    out = np.empty((n_triangles, 3), dtype=np.float32)
    lib.get_triangle_geometry(xy, z, triangles, out, n_triangles)
    return out


def get_bounds(geom):
    """Just return the bounding box for a geometry represented as a numpy array (or a list of arrays correpsponding to a polygon)."""
    if isinstance(geom, list):
        arr = geom[0]
    else:
        arr = geom
    bbox = np.empty((4,), dtype=np.float64)
    bbox[0:2] = np.min(arr[:, :2], axis=0)
    bbox[2:4] = np.max(arr[:, :2], axis=0)
    return bbox


def points2ogr_polygon(points):
    """Construct a OGR polygon from an input point list (not closed)"""
    # input an iterable of 2d 'points', slow interface for large collections...
    s = ogr.Geometry(ogr.wkbLineString)
    for p in points:
        s.AddPoint_2D(p[0], p[1])
    s.AddPoint_2D(points[0][0], points[0][1])  # close
    p = ogr.BuildPolygonFromEdges(ogr.ForceToMultiLineString(s))
    return p


def bbox_intersection(bbox1, bbox2):
    # simple intersection of two boxes given as (xmin,ymin,xmax,ymax)
    box = [-1, -1, -1, -1]
    box[0] = max(bbox1[0], bbox2[0])
    box[1] = max(bbox1[1], bbox2[1])
    box[2] = min(bbox1[2], bbox2[2])
    box[3] = min(bbox1[3], bbox2[3])
    if box[0] >= box[2] or box[1] >= box[3]:
        return None
    return box


def bbox_to_polygon(bbox):
    """Convert a box given as (xmin,ymin,xmax,ymax) to a OGR polygon geometry."""
    points = ((bbox[0], bbox[1]), (bbox[2], bbox[1]), (bbox[2], bbox[3]), (bbox[0], bbox[3]))
    poly = points2ogr_polygon(points)
    return poly


def cut_geom_to_bbox(geom, bbox):
    # input a bounding box as returned from get_bounds...
    poly = bbox_to_polygon(bbox)
    return poly.Intersection(geom)


def points_in_polygon(points, rings):
    """
    Calculate a mask indicating whether points lie within a polygon.
    Args:
        points: 2d numpy array ( shape (n,2) ).
        rings: The list of rings (outer rings first) as returned by ogrpoly2array.
    Returns:
        1d numpy boolean array.
    """
    verts = np.empty((0, 2), dtype=np.float64)
    nv = []
    for ring in rings:
        if not (ring[-1] == ring[0]).all():
            raise ValueError("Polygon boundary not closed!")
        verts = np.vstack((verts, ring))
        nv.append(ring.shape[0])
    nv = np.asarray(nv, dtype=np.uint32)
    out = np.empty((points.shape[0],), dtype=np.bool)  # its a byte, really
    some = lib.p_in_poly(points, out, verts, points.shape[0], nv, len(rings))
    return out


def get_boundary_vertices(validity_mask, poly_mask, triangles):
    # Experimental: see pointcloud.py for explanation.
    out = np.empty_like(poly_mask)
    lib.mark_bd_vertices(
        validity_mask,
        poly_mask,
        triangles,
        out,
        validity_mask.shape[0],
        poly_mask.shape[0])
    return out


def linestring_displacements(xy):
    """
    Calculate the 'normal'/displacement vectors needed to buffer a line string (xy array of shape (n,2))
    """
    dxy = xy[1:] - xy[:-1]
    ndxy = np.sqrt((dxy**2).sum(axis=1)).reshape((dxy.shape[0], 1))  # should return a 1d array...
    hat = np.column_stack((-dxy[:, 1], dxy[:, 0])) / ndxy  # dxy should be 2d
    normals = hat[0]
    # calculate the 'inner normals' - if any...
    if hat.shape[0] > 1:
        dots = (hat[:-1] * hat[1:]).sum(axis=1).reshape((hat.shape[0] - 1, 1))
        # dot of inner normal with corresponding hat should be = 1
        #<(v1+v2),v1>=1+<v1,v2>=<(v1+v2),v2>
        # assert ( not (dots==-1).any() ) - no 180 deg. turns!
        alpha = 1 / (1 + dots)
        # should be 2d - even with one row - else use np.atleast_2d
        inner_normals = (hat[:-1] + hat[1:]) * alpha
        normals = np.vstack((normals, inner_normals))
    normals = np.vstack((normals, hat[-1]))
    return normals


def unit_test(n=1000):
    verts = np.asarray(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)), dtype=np.float64)
    pts = np.random.rand(n, 2).astype(np.float64)  # n points in unit square
    M = points_in_buffer(pts, verts, 2)
    assert M.sum() == n
    M = points_in_polygon(pts, [verts])
    assert M.sum() == n
    pts += (2.0, 2.0)
    M = points_in_polygon(pts, [verts])
    assert not M.any()


if __name__ == "__main__":
    unit_test()
