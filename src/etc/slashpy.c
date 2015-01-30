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
#include "slash.h"
unsigned long py_get_num_records(LAS *h){
	return h->number_of_point_records;
}

/*buf must be of size 6*/
void py_get_extent(LAS *h,double *buf){
	buf[0]=h->x_min;
	buf[1]=h->y_min;
	buf[2]=h->z_min;
	buf[3]=h->x_max;
	buf[4]=h->y_max;
	buf[5]=h->z_max;
}

/*here mask must be of the size reported in number_of_point_records*/
unsigned long py_set_mask(LAS *h, char *mask, int *cs, double *xy_box, double *z_box, int nc){
	unsigned long i=0,count=0, n=h->number_of_point_records;
	int c, j;
	double x,y,z;
	las_seek(h,0,SEEK_SET); /*rewind*/
	while(las_read(h) && i<n){
		x=las_x(h);
		y=las_y(h);
		mask[i]=0;
		i++;
		if (xy_box!=NULL && (x<xy_box[0] || y<=xy_box[1] || x>=xy_box[2] || y>=xy_box[3]))
			continue;
		z=las_z(h);
		if (z_box!=NULL && (z<z_box[0] || z>z_box[1]))
			continue;
		if (nc<=0){
			mask[i-1]=1;
			count++;
			continue;
		}
		c=las_class(h);
		j=0;
		while(c!=cs[j] && j<nc) j++;
		
		if (j==nc)
			continue;
		/*if we got here - then all is good*/
		mask[i-1]=1;
		count++;
	}
	return count;
}



/* if given - mask must be of the size reported in number_of_point_records*/
unsigned long py_get_records(LAS *h, double *xy, double *z, int *c, int *pid, int *return_number, char *mask, unsigned long buf_size){
	unsigned long i=0,j=0, n=h->number_of_point_records;
	if (mask)
		las_seek(h,0,SEEK_SET); /*rewind if mask is set*/
	while(i<buf_size && j<n && las_read(h)){ /* if buf_size < n - avoid reading one record which is discarded...*/
		/*if mask is given - use it*/
		if (mask==NULL || (mask!=NULL && mask[j])){
			if (xy){
				xy[2*i]=las_x(h);
				xy[2*i+1]=las_y(h);
			}
			if (z)
				z[i]=las_z(h);
			if (c)
				c[i]=las_class (h);
			if (pid)
				pid[i]=las_point_source_id(h);
			if (return_number)
				return_number[i]=las_return_number(h);
			i++;
		}
		j++;
	}
	return i;
}

