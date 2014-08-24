int p_in_poly(double *p_in, char *mout, double *verts, unsigned int np, unsigned int  *nv, unsigned int n_rings);
void p_in_buf(double *p_in, char *mout, double *verts, unsigned long np, unsigned long nv, double d);
void get_triangle_geometry(double *xy, double *z, int *triangles, float *out , int ntriangles);
int fill_spatial_index(int *sorted_flat_indices, int *index, int npoints, int max_index);
typedef double(*PC_FILTER_FUNC)(int, int*, double* , double* , double,  int);