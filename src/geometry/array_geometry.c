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
#define ABS(x)  (x>0? x: -x)
#define DET(x,y)  (x[0]*y[1]-x[1]*y[0])

static double d_p_line(double *p1,double *p2, double *p3);
static double d_p_line_string(double *p, double *verts, unsigned long nv);
static int do_lines_intersect(double *p1,double *p2, double *p3, double *p4);


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
