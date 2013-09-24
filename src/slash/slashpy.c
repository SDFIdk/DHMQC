#include <stdlib.h>
#include <stdio.h>
#include "slash.h"
unsigned long py_get_num_records(LAS *h){
	return h->number_of_point_records;
}
unsigned long py_get_records(LAS *h, double *xy, double *z, int *c, unsigned long buf_size){
	unsigned long i=0;
	while(las_read(h) && i<buf_size){
		if (xy){
			xy[2*i]=las_x(h);
			xy[2*i+1]=las_y(h);
		}
		if (z)
			z[i]=las_z(h);
		if (c)
			c[i]=las_classification (h);
		i++;
	}
	return i;
}

