/*
* Copyright (c) 2015, Danish Geodata Agency <gst@gst.dk>
 * 
 * Permission to use, copy, modify, and/or distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 * 
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 * 
 */
int p_in_poly(double *p_in, char *mout, double *verts, unsigned int np, unsigned int  *nv, unsigned int n_rings);
void p_in_buf(double *p_in, char *mout, double *verts, unsigned long np, unsigned long nv, double d);
void get_triangle_geometry(double *xy, double *z, int *triangles, float *out , int ntriangles);
void fill_it_up(unsigned char *out, unsigned int *hmap, int rows, int cols, int stacks);
void find_floating_voxels(int *lab,  int *out, int gcomp, int rows, int cols, int stacks);
int fill_spatial_index(int *sorted_flat_indices, int *index, int npoints, int max_index);
typedef double(*FILTER_FUNC)(double *, double , int*, double* , double* , double, double, void*);
void pc_min_filter(double *xy, double *pc_xy, double *pc_z, double *z_out, double filter_rad, double nd_val, int *spatial_index, double *header, int npoints);
void pc_spike_filter(double *xy, double *z, double *pc_xy, double *pc_z, double *z_out, double filter_rad, double tanv2, double zlim, int *spatial_index, double *header, int npoints);
void pc_mean_filter(double *xy, double *pc_xy, double *pc_z, double *z_out, double filter_rad, double nd_val,int *spatial_index, double *header, int npoints);
void pc_median_filter(double *xy, double *pc_xy, double *pc_z, double *z_out, double filter_rad, double nd_val, int *spatial_index, double *header, int npoints);
void pc_idw_filter(double *xy, double *pc_xy, double *pc_z, double *z_out, double filter_rad, double nd_val, int *spatial_index, double *header, int npoints);
void pc_var_filter(double *xy, double *pc_xy, double *pc_z, double *z_out, double filter_rad, double nd_val, int *spatial_index, double *header, int npoints);
void pc_density_filter(double *xy, double *pc_xy, double *pc_z, double *z_out, double filter_rad, int *spatial_index, double *header, int npoints);
void moving_bins(double *z, int *nout, double rad, int n);