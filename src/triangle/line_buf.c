/*
* Super simple "is point in buffer around line string implementation"
*/
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#define DOT(x,y) (x[0]*y[0]+x[1]*y[1])
#define MIN(x,y)  ((x<y) ? x:y)


static double d_p_line(double *p1,double *p2, double *p3);
void p_in_buf(double *p_in, char *mout, double *verts, unsigned long np, unsigned long nv, double d);

/*returns squared distance*/
static double d_p_line(double *p1,double *p2, double *p3){
	double p[2],v[2],dot1,dot2;
	p[0]=p1[0]-p2[0];
	p[1]=p1[1]-p2[1];
	v[0]=p3[0]-p2[0];
	v[1]=p3[1]-p2[1];
	dot1=DOT(p,v);
	if (dot1<0){
		//puts("In da start!");
		return DOT(p,p);
	}
	dot2=DOT(v,v);
	if (dot1<dot2){
		//puts("Yep in da middle!");
		dot1/=dot2;
		v[0]=p[0]-v[0]*dot1;
		v[1]=p[1]-v[1]*dot1;
		return DOT(v,v);
	}
	//puts("in da end");
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
		//printf("d is: %.4f, vertex: %d\n",d,i);
		d0=d_p_line(p,verts+2*i,verts+2*(i+1));
		//printf("d0 is: %.4f\n",d0);
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

#ifdef HYDI_BYDI
int main(int argc, char **argv){
	double verts[8]={0,0,1,0,1,1,2,1};
	double xy[2],d;
	int i;
	if (argc<3){
		puts("Two points, please!");
		return 1;
	}
	xy[0]=atof(argv[1]);
	xy[1]=atof(argv[2]);
	printf("Distance from (%.2f,%.2f) to line is: %.4f\n",xy[0],xy[1],d_p_line_string(xy,verts,4));
	for(i=0; i<1e6; i++)
		d=d_p_line_string(xy,verts,4);
	return 0;
}
#endif		