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
/*
* Super simple "is point in buffer around line string implementation"
*/
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include "array_geometry.h"
#define DOT(x,y) (x[0]*y[0]+x[1]*y[1])
#define MIN(x,y)  ((x<y) ? x:y)
#define MAX(a,b) (a>b ? a: b)
#define MEPS -1e-8
#define ABS(x)  ((x)>0? (x): -(x))
#define DET(x,y)  (x[0]*y[1]-x[1]*y[0])
#define SQUARE(x) (x)*(x)

static double d_p_line(double *p1,double *p2, double *p3);
static double d_p_line_string(double *p, double *verts, unsigned long nv);
static int do_lines_intersect(double *p1,double *p2, double *p3, double *p4);
static int get_points_around_center(double *xy, double *pc_xy, double search_rad, int *index_buffer, int buf_size, int *spatial_index, double *header, int size_pc);
static void pc_apply_filter(double *pc_xy, double *pc_z, double *vals_out, double filter_rad, int *spatial_index, double *header, int npoints, PC_FILTER_FUNC filter_func, double *params, double nd_val);
static double faithfull_thinning_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int nfound);
static double spike_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int n_found);
static double isolation_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int nfound);
static double wire_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int nfound);
static double mean_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int nfound);
static double moving_correlation_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int n_found);


/*almost copy from trig_index.c*/
static int do_lines_intersect(double *p1,double *p2, double *p3, double *p4){
	double v1[2],v2[2],v3[3],st[2],D;
	int i;
	for(i=0; i<2; i++){
		v1[i]=p2[i]-p1[i];
		v2[i]=p3[i]-p4[i];
		v3[i]=p3[i]-p1[i];
	}
	D=DET(v1,v2); 
	if (ABS(D)<1e-10)
		return 0; /*improve*/
	st[0]=(v2[1]*v3[0]-v2[0]*v3[1])/D;
	st[1]=(-v1[1]*v3[0]+v1[0]*v3[1])/D;
	
	if (st[0]>MEPS && st[0]<1-MEPS && st[1]>MEPS && st[1]<1-MEPS)
		return 1;
	
	return 0;
}
	



int p_in_poly(double *p_in, char *mout, double *verts, unsigned int np, unsigned int *nv, unsigned int n_rings){
	unsigned int i,j,k,n=0, n_hits;
	double bounds[4]; /*x1,x2,y1,y2*/
	double p_end[2],*pv;
	bounds[0]=verts[0];
	bounds[1]=verts[0];
	bounds[2]=verts[1];
	bounds[3]=verts[1];
	/* printf("Npoints: %d ,Nrings: %d\n",np,n_rings); */
	/*loop over outer ring*/
	for(i=0; i<nv[0]; i++){
		bounds[0]=MIN(bounds[0],verts[2*i]);
		bounds[1]=MAX(bounds[1],verts[2*i]);
		bounds[2]=MIN(bounds[2],verts[2*i+1]);
		bounds[3]=MAX(bounds[3],verts[2*i+1]);
	}
	/* printf("Bounds %.3f %.3f %.3f %.3f\n",bounds[0],bounds[1],bounds[2],bounds[3]);*/
	
	for(i=0; i< np; i++){
		mout[i]=0;
		if (p_in[2*i]<bounds[0] || p_in[2*i]>bounds[1] || p_in[2*i+1]<bounds[2] || p_in[2*i+1]>bounds[3]){
			/* printf("out of bounds: %.3f %.3f\n",p_in[2*i],p_in[2*i+1]);*/
			continue;
		}
		p_end[1]=p_in[2*i+1];
		p_end[0]=bounds[1]+1; /*almost an infinite ray :-) */
		n_hits=0;
		/*printf("p_in: %.2f %.2f\n",p_in[2*i],p_in[2*i+1]);*/
		pv=verts;
		for(j=0; j<n_rings; j++){
			/*printf("Ring: %d, nv: %d\n",j,nv[j]);*/
			for (k=0; k<nv[j]-1; k++){
				n_hits+=do_lines_intersect(p_in+2*i,p_end,pv,pv+2);
				/*printf("Point: %d, line: %d, (%.2f %.2f, %.2f %.2f), nhits: %d\n",i,k,*pv,*(pv+1),*(pv+2),*(pv+3),n_hits);*/
				pv+=2;
			}
			pv+=2; 
		}
		
		if (n_hits % 2 ==1){ 
			mout[i]=1;
			n+=1;
		}
	}
		
	return (n>0) ? 1 : 0;
}




/*returns squared distance*/
static double d_p_line(double *p1,double *p2, double *p3){
	double p[2],v[2],dot1,dot2;
	p[0]=p1[0]-p2[0];
	p[1]=p1[1]-p2[1];
	v[0]=p3[0]-p2[0];
	v[1]=p3[1]-p2[1];
	dot1=DOT(p,v);
	if (dot1<0){
		/*puts("In da start!");*/
		return DOT(p,p);
	}
	dot2=DOT(v,v);
	if (dot1<dot2){
		/*puts("Yep in da middle!");*/
		dot1/=dot2;
		v[0]=p[0]-v[0]*dot1;
		v[1]=p[1]-v[1]*dot1;
		return DOT(v,v);
	}
	/*puts("in da end");*/
	v[0]=p3[0]-p1[0];
	v[1]=p3[1]-p1[1];
	return DOT(v,v);
	/*<x,v> v /<v,v> ,, |<x,v> v /<v,v>|^2 < <v,v> <-> <x,y> < <v,v> */
}
/*returns squared distance*/
static double d_p_line_string(double *p, double *verts, unsigned long nv){
	unsigned long i;
	double d0, d=d_p_line(p,verts,verts+2);
	for (i=1; i<nv-1; i++){
		/*printf("d is: %.4f, vertex: %d\n",d,i);*/
		d0=d_p_line(p,verts+2*i,verts+2*(i+1));
		/*printf("d0 is: %.4f\n",d0);*/
		d=MIN(d,d0);
		
	}
	return d;
}

void p_in_buf(double *p_in, char *mout, double *verts, unsigned long np, unsigned long nv, double d){
	unsigned long i;
	double d2=d*d;
	for(i=0; i< np; i++)
		mout[i]=(d_p_line_string(p_in+2*i,verts,nv)<d2) ? 1 :0;
	return;
}


static void compute_normal(double *p1, double *p2, double *p3,double z1, double z2, double z3, double *n){
	double v1[3],v2[3];
	int i;
	/* compute two 3d vectors*/
	for(i=0;i<2;i++){
		v1[i]=p2[i]-p1[i];
		v2[i]=p3[i]-p1[i];
	}
	v1[2]=z2-z1;
	v2[2]=z3-z1;
	n[0]=v1[1]*v2[2]-v1[2]*v2[1];
	n[1]=-(v1[0]*v2[2]-v1[2]*v2[0]);
	n[2]=v1[0]*v2[1]-v1[1]*v2[0];
}

void get_triangle_geometry(double *xy, double *z, int *triangles, float *out , int ntriangles){
	int i;
	double n[3],*p1,*p2,*p3,z1,z2,z3,x1,x2,y1,y2,zmax,zmin;
	for(i=0;i<ntriangles;i++){
		p1=xy+2*triangles[3*i];
		p2=xy+2*triangles[3*i+1];
		p3=xy+2*triangles[3*i+2];
		z1=z[triangles[3*i]];
		z2=z[triangles[3*i+1]];
		z3=z[triangles[3*i+2]];
		compute_normal(p1,p2,p3,z1,z2,z3,n);
		/*compute bbox and tanv2 - angle between z axis and normal - thus large values are critical, 1 correponds to 45 deg*/
		out[3*i]=(float) ((n[0]*n[0]+n[1]*n[1])/(n[2]*n[2])); /*hmm could be inf*/
		x1=MIN(MIN(p1[0],p2[0]),p3[0]);
		x2=MAX(MAX(p1[0],p2[0]),p3[0]);
		y1=MIN(MIN(p1[1],p2[1]),p3[1]);
		y2=MAX(MAX(p1[1],p2[1]),p3[1]);
		zmax=MAX(MAX(z1,z2),z3);
		zmin=MIN(MIN(z1,z2),z3);
		out[3*i+1]=(float) MAX(x2-x1,y2-y1);
		out[3*i+2]=(float) (zmax-zmin);
	}
	return;
}

/***************************
** Fast filling of ground below DTM
** just fill ones below dtm
****************************/

void fill_it_up(unsigned char *out, unsigned int *hmap, int rows, int cols, int stacks){
	int z,i,j,k;
	for(i=0; i<rows; i++){
		for(j=0; j<cols; j++){
			z=hmap[i*cols+j];
			/*voxel (i,j,k) filling height k->k+1, e.g. h=0.5 lies at stack index 0*/
			for(k=0; k<z && k<stacks; k++){
				out[i*cols*stacks+j*stacks+k]=1;
			}
			
		}
	}
}

/* mark things thats not connected to  ground - return the vertical distance to top of ground component - can be negative*/
void find_floating_voxels(int *lab, int *out, int gcomp, int rows, int cols, int stacks){
	int i,j,k,z,L;
	for(i=0; i<rows; i++){
		for(j=0; j<cols; j++){
			/*loop up at (i,j) - find max height of ground component*/
			z=0;
			for(k=0; k<stacks; k++){
				L=lab[i*cols*stacks+j*stacks+k];
				if (L==gcomp)
					z=k;
				
			}
			for(k=0; k<stacks; k++){
				L=lab[i*cols*stacks+j*stacks+k];
				if (L==0)
					continue;
				if (L!=gcomp)
					out[i*cols*stacks+j*stacks+k]=(k-z);
				
			}
		}
	}
}	



/***************************************
*  
*   Filtering stuff below here
*
*
*
*
***************************************/

	

/*fill a spatial index for a pointcloud*/
int fill_spatial_index(int *sorted_flat_indices, int *index, int npoints, int max_index){
	int i, ind, current_index=sorted_flat_indices[0];
	index[current_index]=0;
	for(i=1; i<npoints; i++){
		ind=sorted_flat_indices[i];
		if (ind>(max_index-1))
			return 1;
		if (ind>current_index){
			index[ind]=i;
			current_index=ind;
		}
	}
	return 0;
}

/*return indices of points around given center xy - terminated by a negative number
* header consists of: [ncols, nrows, x1, y2, cs] */
static int get_points_around_center(double *xy, double *pc_xy, double search_rad, int *index_buffer, int buf_size, int *spatial_index, double *header, int size_pc){
	int c,r, r_l, c_l, ncols, nrows, ncells, ind, current_index, pc_index, nfound;
	double sr2,sr2c, cs, x1, y2, d;
	ncols=(int) header[0];
	nrows=(int) header[1];
	x1=header[2];
	y2=header[3];
	cs=header[4];
	ncells=(int) ((search_rad/cs))+1;
	sr2c=SQUARE(ncells);
	sr2=SQUARE(search_rad);
	c=(int) ((xy[0]-x1)/cs);
	r=(int) ((y2-xy[1])/cs);
	nfound=0;
	/*check if we're in the covered region*/
	if ((c+ncells)<0 || (c-ncells)>=ncols || (r+ncells)<0 || (r-ncells)>=nrows){
		return 0;
	}
	for (r_l=MAX(r-ncells,0); r_l<=MIN(r+ncells,nrows-1); r_l++){
		/*loop along a row - set start and end index*/
		for(c_l=MAX(c-ncells,0);c_l<=MIN(c+ncells,ncols-1);c_l++){
		/*speed up for small cell tiling by checking cell coordinate distance...*/
			d=SQUARE(r_l-r)+SQUARE(c_l-c);
			if (d>(sr2c+1)){ /*test logic here*/
				continue;
			}
			/*now set the pc at that index*/
			ind=r_l*ncols+c_l;
			pc_index=spatial_index[ind];
			if (pc_index<0)
				continue; /*nothing in that cell*/
			current_index=ind;
			while(current_index==ind && nfound<buf_size && pc_index<size_pc){
				d=SQUARE(pc_xy[2*pc_index]-xy[0])+SQUARE(pc_xy[2*pc_index+1]-xy[1]);
				if (d<=sr2){
					/* append to list*/
					index_buffer[nfound]=pc_index;
					nfound++;
					/*printf("pc_index: %d\n",pc_index);*/
				}
				pc_index++;
				/*calc the magic flat index*/
				current_index=((int) ((y2-pc_xy[2*pc_index+1])/cs))*ncols+((int) ((pc_xy[2*pc_index]-x1)/cs));
				
			}
		}
	}
	return nfound;
}

static void pc_apply_filter(double *pc_xy, double *pc_z, double *vals_out, double filter_rad, int *spatial_index, double *header, 
int npoints, PC_FILTER_FUNC filter_func, double *params, double nd_val){
	int i, nfound, index_buffer[16384], buf_size=16384, nwarn=0; /*buf size could be put in a define and define at compile time*/
	/*unsigned long mf=0;*/
	for(i=0; i<npoints; i++){
		vals_out[i]=nd_val;
		nfound=get_points_around_center(pc_xy+2*i,pc_xy, filter_rad, index_buffer, buf_size, spatial_index, header, npoints);
		if (nfound>0)
			vals_out[i]=filter_func(i,index_buffer,pc_xy,pc_z,filter_rad,params,nfound); /*the filter func should know how many params there are - or we can terminate list by something...*/
		if (nfound==buf_size && nwarn<100){
			puts("Overflow - use a smaller filter man...");
			nwarn++;
		}
		if (i>0 && i % 1000000 == 0){
			printf("Filtering - done: %d\n",i);
		}
		/*DEBUG:
		 mf+=nfound;
		 if (i%100000==0 && i>0){
			printf("Done %d, mf: %.2f\n",i,mf/((double)i));
			for(j=0;j<nfound;j++){
				printf("%d %.2f ",index_buffer[j],sqrt(pow(pc_xy[2*i]-pc_xy[2*index_buffer[j]],2)+pow(pc_xy[2*i+1]-pc_xy[2*index_buffer[j]+1],2)));
			}
			puts("\nda end");
		}*/
		
	}
}

static double min_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int nfound){
	int j;
	double m=pc_z[i];
	for(j=0; j<nfound; j++){
		m=MIN(m,pc_z[indices[j]]);
	}
	return m;
}

/*like a bird on a wire - like a drunken midnight quire...
* Check if the geometry looks like a wire point 
* In combination with spike-filter this might reveal wire points
* EDIT: this is just stupid -- should be done on a more global level...
*/
static double wire_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int nfound){
	int j,k,n_level=0;
	double z,x,y,z1,z2,zz,dx,dy,dz,*dxs,*dys,wire_level=params[0],res=0;
	z=pc_z[i];
	z1=(z2=z);
	x=pc_xy[2*i];
	y=pc_xy[2*i+1];
	dxs=malloc(nfound*sizeof(double));
	if (!dxs){
		puts("Failed to allocate space!");
		return 0;
	}
	dys=malloc(nfound*sizeof(double));
	if (!dys){
		puts("Failed to allocate space!");
		free(dxs);
		return 0;
	}
	for(j=0; j<nfound; j++){
		k=indices[j];
		zz=pc_z[k];
		z1=MIN(zz,z1);
		z2=MAX(zz,z2);
		dz=z-zz;
		if (ABS(dz)<wire_level && k!=i){
			dx=pc_xy[2*k]-x;
			dy=pc_xy[2*k+1]-y;
			dxs[n_level]=dx;
			dys[n_level]=dy;
			n_level++;
		}
		
	}
	/*TODO: just a test... probably needs a real Radon transform...*/
	if (n_level>2){
		double ms=0,chi2=0,delta;
		for(j=0;j<n_level;j++){
			if (ABS(dxs[j])>1e-8){
				ms+=(dys[j]/dxs[j]);
			}
		}
		ms/=n_level;
		for(j=0;j<n_level;j++){
			delta=(ms*dxs[j]-dys[j]);
			chi2+=delta*delta;
		}
		chi2=sqrt(chi2/n_level);
		if (chi2<0.05)
			res=1;
	}
		
		
	free(dxs);
	free(dys);
	return res;
}

/* return 0 if isolated return 1  if not isolated - can be used to remove points inside buildings... for example*/
static double isolation_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int nfound){
	double dlim2=params[0],zz,z1,z2,x,y,z,dx,dy,dz,dmin,d;
	int j,k, above=0,below=0;
	z=pc_z[i];
	z1=z;
	z2=z;
	x=pc_xy[2*i];
	y=pc_xy[2*i+1];
	dmin=1e12; /*TODO: should be HUGE_VAL or something*/
	for(j=0; j<nfound && dmin>dlim2; j++){
		k=indices[j];
		zz=pc_z[k];
		z1=MIN(zz,z1);
		z2=MAX(zz,z2);
		if (k!=i){
			dz=z-zz;
			if (dz>0)
				below=1;
			if (dz<0)
				above=1;
			dx=x-pc_xy[2*k];
			dy=y-pc_xy[2*k+1];
			d=(dx*dx)+(dy*dy)+(dz*dz);
			if (d<dmin)
				dmin=d;
		}
		
	}
	
	if (dmin>dlim2 && above && below) /*if we have no points close by - but points well above and below - remove...*/
		return 0;
	return 1;
}

/* moving correlation filter - usefull for classification purposes -to be optimized...*/
static double moving_correlation_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int n_found){
	int j,k,qi,qj,qk,q,shape[6],ret=0;
	/*char *E;*/
	double z,x,y,dx,dy,dz,cxy=params[6],cz=params[7],*elem;
	if (n_found<2) 
		return n_found;
	/*not really needed*/
	for(j=0;j<6;j++){
		shape[j]=(int) params[j]; 
	}
	elem=params+8;
	/*E=calloc(shape[0]*shape[1]*shape[2],sizeof(char));
	if (E==NULL){
		puts("Failed to allocate space!");
		return -1;
	}*/
	/*printf("********\ni:%d, cxy:%.2f cz:%.2f  i0: %d, j0: %d, k0: %d, element[0,0,0]: %.2f\n",i,cxy,cz,shape[3],shape[4],shape[5],elem[0]);
	printf("nfound: %d\n",n_found);*/
	z=pc_z[i];
	x=pc_xy[2*i];
	y=pc_xy[2*i+1];
	for(j=0;j<n_found;j++){
		k=indices[j];
		dz=pc_z[k]-z;
		dx=pc_xy[2*k]-x;
		dy=y-pc_xy[2*k+1]; /*array indexing*/
		qi=((int) (dy/cxy+0.5))+shape[3];
		qj=((int) (dx/cxy+0.5))+shape[4];
		qk=((int) (dz/cz+0.5))+shape[5];
		q=qi*shape[1]*shape[2]+qj*shape[2]+qk;
		/*printf("j: %d, k: %d, ret: %d, qi: %d, qj: %d, qk: %d, q: %d\n",j,k,ret,qi,qj,qk,q);
		printf("dx: %.2f, dy: %.2f, dz: %.2f\n",dx,dy,dz);*/
		if (qi>=0 && qj>=0 && qk>=0 && qi<shape[0] && qj<shape[1] && qk<shape[2] && (elem[q])){
			ret++;
			/*puts("hit");
			E[q]=1;*/
		}
	}
	/*free(E);*/
	return ret;
}

/* A spike is a point, which is a local extrama, and where there are steep edges in all four quadrants. An edge is steep if its slope is above a certain limit and its delta z likewise*/
/* all edges must be steep unless it is smaller than filter_radius*0.2 - so filter_radius is significant here!*/
/* paarams are: tanv2 and  delta-z*/
static double spike_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int n_found){
	int j,k,n_steep=0, n_q1=0, n_q2=0, n_q3=0, n_q4=0, n_all_plus=0, n_all_minus=0, could_be_spike=1;
	double d,dz,dx,dy,mean_dz=0, abs_dz, z=pc_z[i],x=pc_xy[2*i],y=pc_xy[2*i+1],d_lim=SQUARE(f_rad*0.2),slope,tanv2,zlim;
	if (n_found<5) /*not enogh evidence*/
		return 0;
	tanv2=params[0];
	zlim=params[1];
	/*we must ensure that there are points further away than the limit - and that they spread out nicely*/
	for(j=0; j<n_found; j++){
		k=indices[j];
		dx=pc_xy[2*k]-x;
		dy=pc_xy[2*k+1]-y;
		d=SQUARE(dx)+SQUARE(dy);
		dz=pc_z[k]-z;
		n_all_plus+=(dz>1e-6);
		n_all_minus+=(dz<-1e-6);
		slope=SQUARE(dz)/d;
		abs_dz=ABS(dz);
		/* not a local max min*/
		if (n_all_plus>0 && n_all_minus>0){
			could_be_spike=0;
			break;
		}
		/*we must have steep edges in all quadrants*/
		if (slope>tanv2 && abs_dz>zlim){
			n_q1+=(dx>=0 && dy>=0);
			n_q2+=(dx>=0 && dy<0);
			n_q3+=(dx<0   && dy<0);
			n_q4+=(dx<0 && dy>=0);
		}
		else if (d>d_lim){ /*if not steep, must be close!*/
			could_be_spike=0;
			break;
		}
		mean_dz+=dz;
		
	}
	if (!could_be_spike)
		return 0;
	/*OK so we know: local max/min and everything further away than limit is steep*/ 
	if (n_q1>0 && n_q2>0 && n_q3>0 && n_q4>0)
		return mean_dz/n_found;
	return 0;
	
}

/* returns 1 if not flat*/
static double mean_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int nfound){
	int j;
	double m=0;
	for(j=0;j<nfound;j++){
		m+=pc_z[indices[j]];
	}
	m/=nfound;
	return m;
}


/* returns 1 if to be kept...*/
static double faithfull_thinning_filter(int i, int *indices, double *pc_xy, double *pc_z, double f_rad, double *params, int nfound){
	int j;
	double den_cut=params[0], z_cut=params[1];
	double x1=params[2];
	double y2=params[3];
	double cs=params[4];
	long c, r;
	double z1=0.0,z2=0.0,z, dz, zz, den,x,y;
	z=pc_z[i];
	den=nfound/(f_rad*f_rad);
	if (den<den_cut)
		return 1;
	/*if its a local max or min and z is spread out large - keep it. */
	for(j=0;j<nfound;j++){
		zz=pc_z[indices[j]];
		z1=MIN(z1,zz);
		z2=MAX(z2,zz);
	}
	dz=(z2-z1);
	/*always keep local min max*/
	if (dz>z_cut && (z==z1 || z==z2))
		return 1;
	x=pc_xy[2*i];
	y=pc_xy[2*i+1];
	/* ok - so we have many points and its not a local min max --- only keep if array index is even!*/
	c=(long) ((x-x1)/cs);
	r=(long) ((y2-y)/cs);
	if (((c+r)%2)==0)
		return 1;
	return 0;
}

void pc_min_filter(double *pc_xy, double *pc_z, double *z_out, double filter_rad, int *spatial_index, double *header, int npoints){
	pc_apply_filter(pc_xy,pc_z, z_out, filter_rad, spatial_index, header, npoints, min_filter, NULL, -9999); /*nd val meaningless - should always be at least one point in sr*/
}

void pc_mean_filter(double *pc_xy, double *pc_z, double *z_out, double filter_rad,int *spatial_index, double *header, int npoints){
	pc_apply_filter(pc_xy,pc_z, z_out, filter_rad, spatial_index, header, npoints, mean_filter, NULL, -9999); /*nd val meaningless - should always be at least one point in sr*/
}

void pc_isolation_filter(double *pc_xy, double *pc_z, double *z_out, double filter_rad, double dlim,int *spatial_index, double *header, int npoints){
	double params[1];
	params[0]=dlim*dlim; /*square the distance*/
	/*params[1]= (double) keep_extrema;*/
	pc_apply_filter(pc_xy,pc_z, z_out, filter_rad, spatial_index, header, npoints, isolation_filter, params, 0); /*nd val meaningless - should always be at least one point in sr*/
}

void pc_wire_filter(double *pc_xy, double *pc_z, double *z_out, double filter_rad, double wire_height,int *spatial_index, double *header, int npoints){
	double wh=wire_height;
	pc_apply_filter(pc_xy,pc_z, z_out, filter_rad, spatial_index, header, npoints, wire_filter, &wh, 0); /*nd val meaningless - should always be at least one point in sr*/
}

/* tanv2 is tangens of steepnes angle squared */
void pc_spike_filter(double *pc_xy, double *pc_z, double *z_out, double filter_rad, double tanv2, double zlim, int *spatial_index, double *header, int npoints){
	double params[2];
	params[0]=tanv2;
	params[1]=zlim;
	/*printf("Filter rad: %.2f, tanv2: %.2f, zlim: %.2f\n",filter_rad,tanv2,zlim);*/
	pc_apply_filter(pc_xy,pc_z, z_out, filter_rad, spatial_index, header, npoints, spike_filter, params, 0);
	
}

/*params must be [nrows.ncols,nstacks,ci,cj,ck,cs_xy,cs_z]+structure_element*/
void pc_correlation_filter(double *pc_xy, double *pc_z, double *out, double filter_rad, double *params, int *spatial_index, double *header, int npoints){
	/*printf("npoints: %d\n",npoints);*/
	pc_apply_filter(pc_xy,pc_z, out, filter_rad, spatial_index, header, npoints,moving_correlation_filter, params, 0);
}

void pc_thinning_filter(double *pc_xy, double *pc_z, double *z_out, double filter_rad, double zlim, double den_cut, int *spatial_index, double *header, int npoints){
	double params[5],cx=0,cy=0,cs=0.01; /*for now set cs here*/
	int i;
	for(i=0; i<npoints; i++){
		cx+=pc_xy[2*i]/npoints;
		cy+=pc_xy[2*i+1]/npoints;
	}
	params[0]=den_cut;
	params[1]=zlim; /*cut off for when something interseting is happening and we need to keep local min / max*/
	params[2]=cx;
	params[3]=cy;
	params[4]=cs;
	pc_apply_filter(pc_xy,pc_z, z_out, filter_rad, spatial_index, header, npoints, faithfull_thinning_filter, params, 0); /*nd_val not really interesting here*/
}


/* A triangle based 'filter' - on  input zout should be a copy of z */

void tri_filter_low(double *z, double *zout, int *tri, double cut_off, int ntri){
	int i,j,m,I[3];
	double zt[3];
	for(i=0;i<ntri;i++){
		for(j=0;j<3;j++){
			I[j]=tri[3*i+j];
			zt[j]=z[I[j]];
		}
		for(j=0;j<3;j++){
			m=(j+1)%3;
			if ((zt[j]-zt[m])>cut_off){
				zt[j]=zt[m];
				zout[I[j]]=MIN(zt[m],zout[I[j]]);
			}
		}
	}
}

/* MASK based raster filters*/

void masked_mean_filter(float *dem, float *out, char *mask, int filter_rad, int nrows, int ncols){
	/*consider what to do about nd_vals - should probably be handled by caller */
	int i,j,i1,i2,j1,j2,m,n,ind1,ind2,used;
	double v;
	for(i=0 ; i<nrows ; i++){
		for(j=0; j<ncols ; j++){
			ind1=i*ncols+j;
			if (!mask[ind1])
				continue;
			used=0;
			i1=MAX((i-filter_rad),0);
			i2=MIN((i+filter_rad),(nrows-1));
			j1=MAX((j-filter_rad),0);
			j2=MIN((j+filter_rad),(ncols-1));
			used=0;
			v=0.0;
			for(m=i1; m<=i2; m++){
				for(n=j1; n<=j2; n++){
					ind2=m*ncols+n;
					if (mask[ind2]){
						used++;
						v+=(double) dem[ind2];
					}
				}
			}
			/*must be at least one used - well check anyways!*/
			if (used>0)
				out[ind1]=(float) (v/used);
		}
	}
}	

/* Wander around along a water mask and expand flood cells - we can make "channels" along large triangles by setting dem-values low there...*/
int flood_cells(float *dem, float cut_off, char *mask, char *mask_out, int nrows, int ncols){
	int i,j,m,n,i1,j1,n_set=0;
	float v,w;
	size_t ind1,ind2;
	for(i=0; i<nrows; i++){
		for(j=0; j<ncols; j++){
			ind1=i*ncols+j;
			if (mask[ind1]){
				/* a window value of one will ensure connectedness*/
				v=dem[ind1];
				for(m=-1; m<=1; m++){
					for(n=-1;n<=1; n++){
						if ((m+n)!=1 && (m+n)!=-1)
							continue;
						i1=(i+n);
						j1=(j+m);
						if (i1<0 || i1>(nrows-1) || j1<0 || j1>(ncols-1))
							continue;
						ind2=i1*ncols+j1;
						w=dem[ind2];
						
						if ((w-v)<=cut_off && !mask[ind2]){
							mask_out[ind2]=1;
							n_set++;
						}
					}
				}
			}
		}
	}
	return n_set;
}
		
void mark_bd_vertices(char *bd_candidates_mask, char *poly_mask, int *triangles, char *bd_mask_out, int ntriangles, int np){
	int i,j,v;
	for(i=0; i<np; i++) bd_mask_out[i]=0;
	for(i=0; i<ntriangles; i++){
		if (bd_candidates_mask[i]){ /*this triangle is long, or steep, or something...*/
			/* check if any of the vertices are inside the 'polygon'*/
			for(j=0; j<3; j++){
				v=triangles[3*i+j];
				if (poly_mask[v])
					bd_mask_out[v]=1;
			}
		}
	}
	return;
}
		
/* rolling z binning for radon transform 
* input a sorted list of values - spool through and report the number of pts rad below and rad ahead
*/
void moving_bins(double *z, int *nout, double rad, int n){
	int i=0,j=0,nhere=0;
	double z0;
	/*two locaters - one should always be size ahead of the other*/
	for(i=0;i<n;i++){
		z0=z[i]; /*the pt.*/
		/*spool ahead*/
		j=i;
		nhere=0;
		while((z[j]-z0)<rad && j<n){
			j++;
		}
		nhere+=(j-i); /* counting the point also*/
		j=i;
		/*spool back*/
		while ((z0-z[j])<rad && j>=0){
			j--;
		}
		nhere+=(i-j);
		nout[i]=nhere-1; /*subtract one of the two extra counts*/
			
	}
}

	


#ifdef SVEND_BENT
int main(int argc, char **argv){
	double verts[20]={0,0,1,0,1,1,0,1,0,0,0.3,0.3,0.6,0.3,0.6,0.6,0.3,0.6,0.3,0.3};
	unsigned int nv[2]={5,5};
	double xy[2],d;
	char mask[1];
	int i,n;
	if (argc<3){
		puts("Two coords, please!");
		return 1;
	}
	xy[0]=atof(argv[1]);
	xy[1]=atof(argv[2]);
	printf("Distance from (%.2f,%.2f) to line is: %.4f\n",xy[0],xy[1],d_p_line_string(xy,verts,4));
	n=p_in_poly(xy,mask,verts,1,nv,2);
	printf("Return code %d, point in poly: %d\n",n,mask[0]);
	return 0;
}
#endif		
