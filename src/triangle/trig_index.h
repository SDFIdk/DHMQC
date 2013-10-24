struct index{
	int ncols,npoints,ntri,ncells;
	double extent[4];
	double cs;
	int **index_arr;
};

typedef struct index spatial_index;



void inspect_index(spatial_index *ind, char *buf, int buf_len);
int line_intersection(double *p1,double *p2, double *p3, double *p4, double *out);
spatial_index *build_index(double *pts, int *tri, double cs, int n, int m);
/*void find_triangle(double *pts, int *out, spatial_index *ind, double *eq, int np);*/
void find_triangle(double *pts, int *out, double *base_pts,int *tri, spatial_index *ind, char *mask, int np);
/*void find_appropriate_triangles(double *pts, int *out, double *base_pts, double *base_z, int *tri, spatial_index *ind, int np, double tol_xy, double tol_z);
void interpolate(double *pts, double *z, double *out, double nd_val, double *eq, int *tri, spatial_index *ind, int np);*/
void interpolate(double *pts, double *base_pts, double *base_z, double *out, double nd_val, int *tri, spatial_index *ind, char *mask, int np);
void optimize_index(spatial_index *ind);
void free_index(spatial_index *ind);