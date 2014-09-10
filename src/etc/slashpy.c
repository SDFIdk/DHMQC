#include "slash.h"
unsigned long py_get_num_records(LAS *h){
	return h->number_of_point_records;
}

/* for now we can input a bbox to filter - if no filter input NULL - otherwise an array [x1,y1,x2,y2] and same for z, NULL or [z1,z2]*/
unsigned long py_get_records(LAS *h, double *xy, double *zs, int *c, int *pid, int *return_number, double *xy_box, double *z_box, unsigned long buf_size){
	/* TODO: if a lot of filtering needs to be done - probably implement a filtering string. But that doesn't seem to be the use case right now*/
	unsigned long i=0;
	double x,y,z;
	while(las_read(h) && i<buf_size){
		x=las_x(h);
		y=las_y(h);
		z=las_z(h);
		if (xy_box!=NULL && (x<xy_box[0] || y<=xy_box[1] || x>=xy_box[2] || y>=xy_box[3]))
			continue;
		if (z_box!=NULL && (z<z_box[0] || z>z_box[1]))
			continue;
		if (xy){
			xy[2*i]=x;
			xy[2*i+1]=y;
		}
		if (z)
			zs[i]=z;
		if (c)
			c[i]=las_class (h);
		if (pid)
			pid[i]=las_point_source_id(h);
		if (return_number)
			return_number[i]=las_return_number(h);
		i++;
	}
	return i;
}

