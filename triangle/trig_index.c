/* Builds spatial index of a triangulation - speeds up finding simplices...
*  simlk, aug. 2013
*  compile:  gcc -o libname -shared -O3 trig_index.c
*/
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "trig_index.h"
#define DET(x,y)  (x[0]*y[1]-x[1]*y[0])
#define MAX(a,b) (a>b ? a: b)
#define MIN(a,b)  (a<b ? a:b)
#define MEPS -1e-7
#define ABS(x)  (x>0? x: -x)
#define STEPX(k) (k<2?(k):(3-k))
#define DEFAULT_MASK 100
#define EXTRA_SLOTS  4

static int bc(double *, double *, double *, double *, double *);
static int bc2(double *p0, double *p1, double *p2, double *p3, double *b); /*slightly faster -escapes earlier*/
static int *append(int *list, int n);
static void user2array(double *p, int *carr,double *extent, double cs);
static void user2array2(double *p, double *carr,double *extent, double cs);
static int find(double *pt,double *eq, double *bout, int *list);



/*p1p2  intersects p2p3?
* p1+s(p2-p1)=p3+t(p4-p3) =>
* s(p2-p1)+t(p3-p4)=p3-p1  - MATRIX EQ: A[s,t]^T=V, cols of A are (p2-p1) and (p3-p4)
* v1=p2-p1  => a11=v1[0], a21=v1[1]
* v2=p3-p4 => a12=v2[0], a22=v2[1]
* v3=p3-p1
*/

int line_intersection(segment *l1, segment *l2){
	double v1[2],v2[2],v3[3],st[2],D;
	int i;
	for(i=0; i<2; i++){
		v1[i]=l1->p2[i]-l1->p1[i];
		v2[i]=l2->p1[i]-l2->p2[i];
		v3[i]=l2->p1[i]-l1->p1[i];
	}
	D=DET(v1,v2); 
	if (ABS(D)<1e-8)
		return 0; /*improve*/
	st[0]=(v2[1]*v3[0]-v2[0]*v3[1])/D;
	st[1]=(-v1[1]*v3[0]+v1[0]*v3[1])/D;
	#ifdef MAIN
	printf("s: %.4f, t: %.4f\n",st[0],st[1]);
	#endif
	if (st[0]>MEPS && st[0]<1-MEPS && st[1]>MEPS && st[1]<1-MEPS)
		return 1;
	return 0;
}

int line_intersection2(double *p1,double *p2, double *p3, double *p4, double *out){
	double v1[2],v2[2],v3[3],st[2],D;
	int i;
	for(i=0; i<2; i++){
		v1[i]=p2[i]-p1[i];
		v2[i]=p3[i]-p4[i];
		v3[i]=p3[i]-p1[i];
	}
	D=DET(v1,v2); 
	if (ABS(D)<1e-8)
		return 0; /*improve*/
	st[0]=(v2[1]*v3[0]-v2[0]*v3[1])/D;
	st[1]=(-v1[1]*v3[0]+v1[0]*v3[1])/D;
	#ifdef MAIN
	printf("s: %.4f, t: %.4f\n",st[0],st[1]);
	#endif
	if (st[0]>MEPS && st[0]<1-MEPS && st[1]>MEPS && st[1]<1-MEPS){
		for(i=0;i<2;i++){
			out[i]=p1[i]+st[0]*v1[i];
			#ifdef _DEBUG
			printf("Intersection coord %d: %.3f\n",i,out[i]);
			#endif
		}
		return 1;
	}
	return 0;
}

/*Calculate barycentric coords for p0 relative to triangle p1,p2,p3*/
static int bc(double *p0, double *p1, double *p2, double *p3, double *b){
	double xy0[2],xy1[2],xy2[2];
	double A[3];
	int i;
	for(i=0; i<2; i++){
		xy0[i]=p0[i]-p1[i];
		xy1[i]=p2[i]-p1[i];
		xy2[i]=p3[i]-p1[i];
	}
	A[0]=DET(xy1,xy2);
	A[1]=DET(xy1,xy0);
	A[2]=DET(xy0,xy2);
	b[2]=A[1]/A[0];
	b[1]=A[2]/A[0];
	b[0]=(1.0-b[1]-b[2]);
	if (b[0]>MEPS && b[1]>MEPS && b[2]>MEPS){
		return 1;
	}
	return 0;
}
static int bc2(double *p0, double *p1, double *p2, double *p3, double *b){
	double xy0[2],xy1[2],xy2[2];
	double A[3];
	int i;
	for(i=0; i<2; i++){
		xy0[i]=p0[i]-p1[i];
		xy1[i]=p2[i]-p1[i];
		xy2[i]=p3[i]-p1[i];
	}
	A[0]=DET(xy1,xy2);
	A[1]=DET(xy1,xy0);
	b[2]=A[1]/A[0];
	if (b[2]<MEPS || b[2]>1-MEPS)
		return 0;
	A[2]=DET(xy0,xy2);
	b[1]=A[2]/A[0];
	b[0]=(1.0-b[1]-b[2]);
	if (b[1]>MEPS && b[0]>MEPS){
		return 1;
	}
	return 0;
}
	


/* 'World' to array coords (i,j) */
 static void user2array(double *p, int *carr,double *extent, double cs){
	int i,j;
	i=(int) ((extent[3]-p[1])/cs);
	j=(int) ((p[0]-extent[0])/cs);
	carr[0]=i;
	carr[1]=j;
}

/* World to (x,y) based array coords - x right, y downwards....*/
 static void user2array2(double *p, double *carr,double *extent, double cs){
	carr[1]=((extent[3]-p[1])/cs);
	carr[0]=((p[0]-extent[0])/cs);
}


/* Append positive number to a 'set' of positive numbers... */
static int *append(int *list, int n){
	int found=0,i,room;
	if (list==NULL){
		list=malloc(sizeof(int)*(3+EXTRA_SLOTS));
		list[0]=3+EXTRA_SLOTS; /*number allocated*/
		list[1]=1; /*cells used*/
		list[2]=n;
		return list;
	}
	/* not needed - triangles are treated sequentially */
	/*for(i=2;i<(list[1]+2) && !found; i++){
		if (list[i]==n)
			found=1;
			
	}*/
	if (!found){
		list[1]++;
		room=list[1]+2;
		if (room>list[0]){ /*if not room*/
			list[0]=room+EXTRA_SLOTS;
			list=realloc(list,sizeof(int)*(room+EXTRA_SLOTS)); /*allocate one more slot than needed*/
		}	
		list[list[1]+1]=n;
	}
		
	return list;
	
}

/*Builds the spatial index*/
spatial_index *build_index(double *pts, int *tri, double cs, int n, int m){
	int i,j,k,ncols,nrows,ncells,I[2],J[2],nhits=0,r,c,mask_rows,mask_cols,*vertex;
	double extent[4],*p,p1[2],p2[2],b[3],inters[2],parr[6];
	int **index_arr;
	char *mask, default_mask[DEFAULT_MASK*DEFAULT_MASK],is_allocated=0; /*for storing cell housekeeping array*/
	spatial_index *ind;
	extent[0]=pts[0];
	extent[1]=pts[1];
	extent[2]=pts[0];
	extent[3]=pts[1];
	for (i=1; i<n; i++){
		extent[0]=MIN(extent[0],pts[2*i]);
		extent[1]=MIN(extent[1],pts[2*i+1]);
		extent[2]=MAX(extent[2],pts[2*i]);
		extent[3]=MAX(extent[3],pts[2*i+1]);
	}
	printf("Building index...\nPoint extent: %.2f %.2f %.2f %.2f\n",extent[0],extent[1],extent[2],extent[3]);
	if (cs<0){ /*signal to guess a proper cell size*/
		double den;
		den=n/((extent[2]-extent[0])*(extent[3]-extent[1]));
		cs=sqrt(3/den);
		printf("Auto generating an 'optimal' cell size to: %.3f\n",cs);
		printf("Check memory usage with inspect_index....\n");
	}
	extent[0]-=0.5*cs;
	extent[3]+=0.5*cs;
	ncols=((int) (extent[2]-extent[0])/cs)+2;
	nrows=((int) (extent[3]-extent[1])/cs)+2;
	extent[1]=extent[3]-nrows*cs;
	extent[2]=extent[0]+ncols*cs;
	ncells=ncols*nrows;
	#ifdef _DEBUG
	if (nrows>100 || ncols>100){
		printf("Hello %d %d %.2f\n",nrows,ncols,cs);
		return NULL;
	}
	#endif
	printf("Virtual rows and columns: %d %d , size: %d\n",nrows,ncols,ncells);
	index_arr=calloc(ncells,sizeof(int*));
	/*loop over triangles*/
	for(i=0; i<m; i++){
		#ifdef _DEBUG
		printf("Looking at triangle: %d\n",i);
		#endif
		vertex=tri+3*i;
		for(j=0;j<3;j++){
			p=pts+(*(vertex+j))*2;
			//user2array2(p,parr+2*j,extent,cs);
			parr[2*j+1]=((extent[3]-p[1])/cs);
			parr[2*j]=((p[0]-extent[0])/cs);
			#ifdef _DEBUG
			printf("Array coords of vertex %d: x: %.2f, y: %.2f\n",j,parr[2*j],parr[2*j+1]);
			#endif
			r=(int) parr[2*j+1];
			c=(int) parr[2*j];
			#ifdef _DEBUG
			if (r*c>ncells){
				printf("ost %d %d\n,",r,c);
				return NULL;
			}
			#endif
			if (j==0){
				I[0]=I[1]=r;
				J[0]=J[1]=c;
			}
			else{
				I[0]=MIN(I[0],r);
				J[0]=MIN(J[0],c);
				I[1]=MAX(I[1],r);
				J[1]=MAX(J[1],c);
			}
		}
		mask_rows=(I[1]-I[0]+1);
		mask_cols=(J[1]-J[0]+1);
		#ifdef _DEBUG
		printf("Mask rows: %d, mask cols: %d\n",mask_rows,mask_cols);
		printf("I: %d %d, J: %d %d\n",I[0],I[1],J[0],J[1]);
		if (mask_rows>100 || mask_cols>100)
			return NULL;
		#endif
		mask=NULL;
		if (mask_rows>1 && mask_cols>1){
			/*TODO: transform to array coords to speed things up!!*/
			int chit[2],ch,nintersect;
			if (mask_rows<DEFAULT_MASK && mask_cols<DEFAULT_MASK){
				mask=default_mask;
				for(r=0;r<mask_rows;r++){
					for(c=0;c<mask_cols;c++){
						mask[r*mask_cols+c]=0;
					}
				}
				is_allocated=0;
			}
			else{
				mask=calloc(mask_rows*mask_cols,sizeof(char));
				is_allocated=1;
				if (!mask)
					goto INDEX_ERR;
			}
			for(r=1;r<mask_rows; r++){
				/*loop over inner hlines*/
				
				p1[0]=J[0];
				p2[0]=J[1]+1;
				p1[1]=p2[1]=I[0]+r;
				nintersect=0;
				chit[1]=-1;
				chit[0]=mask_cols+1;
				#ifdef _DEBUG
				printf("Mask row: %d\n",r);
				printf("Line: %.2f,%.2f to %.2f,%.2f\n",p1[0],p1[1],p2[0],p2[1]);
				#endif
				
				for(k=0;k<3;k++){
					if (line_intersection2(p1,p2,parr+k*2,parr+((k+1)%3)*2,inters)){
						/*hmmm might as well calc span here*/
						ch=(int) (inters[0]-J[0]);
						chit[0]=MIN(ch,chit[0]);
						chit[1]=MAX(ch,chit[1]);
						nintersect+=1;
					}
				}
				#ifdef _DEBUG
				printf("Intersections: %d\n",nintersect);
				#endif
				if (nintersect>0){
					for(k=chit[0];k<=chit[1];k++){
						if (nintersect>1)
							mask[(r-1)*mask_cols+k]=1;
						mask[r*mask_cols+k]=1;
					}
				}
				
			}
			
			for(c=1;c<mask_cols; c++){
				/*loop over inner vlines*/
				p1[1]=I[0];
				p2[1]=I[1]+1;
				p1[0]=p2[0]=J[0]+c;
				nintersect=0;
				chit[1]=-1;
				chit[0]=mask_rows+1;
				#ifdef _DEBUG
				printf("Mask col: %d\n",c);
				printf("Line: %.2f,%.2f to %.2f,%.2f\n",p1[0],p1[1],p2[0],p2[1]);
				#endif
				for(k=0;k<3;k++){
					if (line_intersection2(p1,p2,parr+2*k,parr+((k+1)%3)*2,inters)){
						/*hmmm might as well calc span here*/
						ch=(int) (inters[1]-I[0]);
						chit[0]=MIN(ch,chit[0]);
						chit[1]=MAX(ch,chit[1]);
						nintersect+=1;
					}
				}
				
				if (nintersect>0){
					for(k=chit[0];k<=chit[1];k++){
						if (nintersect>1)
							mask[k*mask_cols+(c-1)]=1; /*left*/
						mask[k*mask_cols+c]=1; /*right*/
					}
				}
				
			}
		} /*end dotest*/
		for(r=I[0]; r<=I[1]; r++){
			for(c=J[0];c<=J[1];c++){
				int grid_index=r*ncols+c;
				/*if (i%1000==0)
					printf("r: %d, c: %d, grid_index: %d\n",r,c,grid_index);*/
				if (grid_index<ncells){
					if (mask==NULL || mask[(r-I[0])*mask_cols+(c-J[0])]){
						index_arr[grid_index]=append(index_arr[grid_index],i);
						nhits++;
						/*if (i%1000==0)
							printf("Size of list is now: %d\n",size);*/
							
					}
					
				}
				else
					printf("Bad index %d, I: %d %d, J: %d %d, r: %d, c: %d\n",grid_index,I[0],I[1],J[0],J[1],r,c);
				
				
			}
			
		} /*end insert triangle */
		if (mask!=NULL && is_allocated)
			free(mask);
		
	} /*end loop over triangles*/
	ind=malloc(sizeof(struct index));
	ind->ncols=ncols;
	ind->cs=cs;
	memcpy(ind->extent,extent,sizeof(double)*4);
	ind->index_arr=index_arr;
	ind->npoints=n;
	ind->ntri=m;
	ind->ncells=ncells;
	puts("Done.......\n");
	return ind;
	INDEX_ERR:
		puts("Failed to allocate space!\n");
		if (index_arr)
			/*TODO: free all sub-arrays*/
			free(index_arr);
		return NULL;
	
}

/*Inspect a spatial index */
void inspect_index(spatial_index *ind, char *buf, int buf_len){
	int i, nhit=0,nmax=0;
	unsigned long nbytes=0;
	double nav=0;
	int **arr=ind->index_arr;
	char *pos=buf;
	pos+=sprintf(pos,"************Index inspection***********\n");
	if (pos-buf<buf_len-20)
		pos+=sprintf(pos,"'Cell' size: %.4f\n",ind->cs);
	if (pos-buf<buf_len-20)
		pos+=sprintf(pos,"Ncols: %d\n",ind->ncols);
	if (pos-buf<buf_len-20)
		pos+=sprintf(pos,"Cells: %d\n",ind->ncells);
	if (pos-buf<buf_len-30)
		pos+=sprintf(pos,"Virtual 'Grid' extent: %.2f %.2f %.2f %.2f\n",ind->extent[0],ind->extent[1],ind->extent[2],ind->extent[3]);
	if (pos-buf<buf_len-30)
		pos+=sprintf(pos,"Triangulated points: %d, triangles: %d\n",ind->npoints,ind->ntri);
	nbytes=(ind->ncells*sizeof(int*));
	for (i=0; i<ind->ncells; i++){
		if (arr[i]!=NULL){
			int nhere=arr[i][1];
			nmax=MAX(nhere,nmax);
			nav+=((double) nhere)/ind->ncells;
			nbytes+=(arr[i][0])*sizeof(int);
			nhit++;
		}
	}
	if (pos-buf<buf_len-20)
		pos+=sprintf(pos,"Non-void cells: %d\n",nhit);
	if (pos-buf<buf_len-20)
		pos+=sprintf(pos,"Fraction: %.3f\n",((double) nhit)/ind->ncells);
	if (pos-buf<buf_len-20)
		pos+=sprintf(pos,"List max: %d\n",nmax);
	if (pos-buf<buf_len-20)
		pos+=sprintf(pos,"Average: %.2f\n",nav);
	if (pos-buf<buf_len-20)
		pos+=sprintf(pos,"Memory usage: %.1f kb\n",((double) nbytes)/1e3);
	
}

/* free a spatial index */
void free_index(spatial_index *ind){
	int i;
	if (!ind)
		return;
	for (i=0; i<ind->ncells; i++){
		if (ind->index_arr[i]!=NULL)
			free(ind->index_arr[i]);
	}
	free(ind->index_arr);
	free(ind);
}

void optimize_index(spatial_index *ind){
	int i;
	int **arr=ind->index_arr;
	for (i=0; i<ind->ncells; i++){
		if (arr[i]!=NULL && arr[i][0]>(arr[i][1]+2)){
			arr[i]=realloc(arr[i],sizeof(int)*(arr[i][1]+2));
			arr[i][0]=arr[i][1]+2;
		}
	}
}
/*Find triangles - place indices in out. 
* Requires that the n*3*2 array of 'barycentric transformations' are precalculated...
*/

static int find(double *pt,double *eqs, double *bout, int *list){
	int i,n,j=-1;
	double b[3],p[2],*eq;
	n=list[1];
	for(i=2;i<2+n;i++){
		j=list[i];
		eq=eqs+6*j;
		p[0]=(pt[0]-eq[4]);
		p[1]=(pt[1]-eq[5]);
		b[0]=(eq[0]*p[0]+eq[1]*p[1]);
		if (b[0]<MEPS || b[0]>1-MEPS)
			continue;
		b[1]=(eq[2]*p[0]+eq[3]*p[1]);
		if (b[1]<MEPS || b[1]>1-MEPS)
			continue;
		b[2]=(1.0-b[0]-b[1]);
		#ifdef _DEBUG
		printf("Looking at triangle: %d\n",j);
		printf("Bc-coords: %.3f %.3f %.3f\n",b[0],b[1],b[2]);
		#endif
		if (b[2]>MEPS){
			bout[0]=b[0];
			bout[1]=b[1];
			bout[2]=b[2];
			return j;
		}
				
	}
	return -1;
}



void find_triangle2(double *pts, int *out, double *base_pts,int *tri, spatial_index *ind, int np){
	int I[2],i,j,k,grid_index,ncols,ncells;
	int **arr=ind->index_arr;
	double b[3];
	ncols=ind->ncols;
	ncells=ind->ncells;
	for(i=0; i<np; i++){
		user2array(pts+2*i,I,ind->extent,ind->cs);
		grid_index=I[0]*ncols+I[1];
		#ifdef _DEBUG
		printf("\n******** find *********\n");
		printf("Point %.2f %.2f\n",pts[2*i],pts[2*i+1]);
		printf("Array coords: r %d  c %d\n",I[0],I[1]);
		printf("Grid index: %d\n",grid_index);
		#endif
		out[i]=-1;
		if (0<=grid_index && grid_index<ncells && arr[grid_index]!=NULL){
			int *list=arr[grid_index];
			for(k=2;k<2+list[1];k++){
				j=list[k];
				if (bc2(pts+2*i,base_pts+(2*tri[3*j]),base_pts+(2*tri[3*j+1]),base_pts+(2*tri[3*j+2]),b)){
					out[i]=j;
					break;
				}
			}
				
		}
		
	}
	
}

void find_triangle(double *pts, int *out, spatial_index *ind, double *eq, int np){
	int I[2],i,j,grid_index,ncols,ncells;
	int **arr=ind->index_arr;
	double b[3];
	ncols=ind->ncols;
	ncells=ind->ncells;
	for(i=0; i<np; i++){
		user2array(pts+2*i,I,ind->extent,ind->cs);
		grid_index=I[0]*ncols+I[1];
		#ifdef _DEBUG
		printf("\n******** find *********\n");
		printf("Point %.2f %.2f\n",pts[2*i],pts[2*i+1]);
		printf("Array coords: r %d  c %d\n",I[0],I[1]);
		printf("Grid index: %d\n",grid_index);
		#endif
		out[i]=-1;
		if (0<=grid_index && grid_index<ncells && arr[grid_index]!=NULL){
			j=find(pts+2*i,eq,b,arr[grid_index]);
			if (j>-1)
				out[i]=j;
			
		}
		
	}
	
}

void interpolate(double *pts, double *z, double *out, double nd_val, double *eq, int *tri, spatial_index *ind, int np){
	int I[2],i,j,grid_index,ncols,ncells;
	int **arr=ind->index_arr;
	double b[3],z_int;
	ncols=ind->ncols;
	ncells=ind->ncells;
	for(i=0; i<np; i++){
		user2array(pts+2*i,I,ind->extent,ind->cs);
		grid_index=I[0]*ncols+I[1];
		#ifdef _DEBUG
		printf("\n******** interpolate *********\n");
		printf("Point %.2f %.2f\n",pts[2*i],pts[2*i+1]);
		printf("Array coords: r %d  c %d\n",I[0],I[1]);
		printf("Grid index: %d\n",grid_index);
		#endif
		out[i]=nd_val;
		if (0<=grid_index && grid_index<ncells && arr[grid_index]!=NULL){
			j=find(pts+2*i,eq,b,arr[grid_index]);
			if (j>-1){
				z_int=b[0]*z[tri[3*j]]+b[1]*z[tri[3*j+1]]+b[2]*z[tri[3*j+2]];
				#ifdef _DEBUG
				printf("Hit! z: %.4f\n",z_int);
				#endif
				out[i]=z_int;
				
			}
		}
		
	}
	
}

void interpolate2(double *pts, double *base_pts, double *base_z, double *out, double nd_val, int *tri, spatial_index *ind, int np){
	int I[2],i,j,k,grid_index,ncols,ncells;
	int **arr=ind->index_arr;
	double b[3],z_int;
	ncols=ind->ncols;
	ncells=ind->ncells;
	for(i=0; i<np; i++){
		user2array(pts+2*i,I,ind->extent,ind->cs);
		grid_index=I[0]*ncols+I[1];
		#ifdef _DEBUG
		printf("\n******** interpolate *********\n");
		printf("Point %.2f %.2f\n",pts[2*i],pts[2*i+1]);
		printf("Array coords: r %d  c %d\n",I[0],I[1]);
		printf("Grid index: %d\n",grid_index);
		#endif
		out[i]=nd_val;
		if (0<=grid_index && grid_index<ncells && arr[grid_index]!=NULL){
			int *list=arr[grid_index];
			for(k=2;k<2+list[1];k++){
				j=list[k];
				if (bc2(pts+2*i,base_pts+(2*tri[3*j]),base_pts+(2*tri[3*j+1]),base_pts+(2*tri[3*j+2]),b)){
					z_int=b[0]*base_z[tri[3*j]]+b[1]*base_z[tri[3*j+1]]+b[2]*base_z[tri[3*j+2]];
					out[i]=z_int;
					break;
				}
			}
				
				
				
			
		}
		
	}
	
}
	
void make_grid(double *base_pts,double *base_z, int *tri, double *grid, double nd_val, int ncols, int nrows, double cx, double cy, double xl, double yu, spatial_index *ind){
	int **arr=ind->index_arr,icols,icells,i,j,k,m,I[2];
	long grid_index;
	double xy[2],b[3],z_int;
	icols=ind->ncols;
	icells=ind->ncells;
	for(i=0; i<nrows; i++){
		for(j=0; j<ncols; j++){	
			xy[1]=yu-(i+0.5)*cy;
			xy[0]=xl+(j+0.5)*cx;
			user2array(xy,I,ind->extent,ind->cs);
			grid_index=I[0]*icols+I[1];
			grid[i*ncols+j]=nd_val;
			/*printf("cell: (%d,%d), ind_coords: (%d,%d), real: %.3f %.3f\n",i,j,I[0],I[1],xy[0],xy[1]);
			if (j>10)
				return;*/
			if (0<=grid_index && grid_index<icells && arr[grid_index]!=NULL){
				int *list=arr[grid_index];
				for(k=2;k<2+list[1];k++){
					m=list[k];
					if (bc2(xy,base_pts+(2*tri[3*m]),base_pts+(2*tri[3*m+1]),base_pts+(2*tri[3*m+2]),b)){
						z_int=b[0]*base_z[tri[3*m]]+b[1]*base_z[tri[3*m+1]]+b[2]*base_z[tri[3*m+2]];
						grid[i*ncols+j]=z_int;
						break;
					}
				}
			
			}
		}
	}
}

#ifdef MAIN
int main(void){
	double p1[2]={-1,0};
	double p2[2]={1,0};
	double p3[2]={0,1};
	double p4[2]={0,-1};
	struct segment l1,l2;
	l1.p1=p1;
	l1.p2=p2;
	l2.p1=p3;
	l2.p2=p4;
	printf("Intersects? %d\n",line_intersection(&l1,&l2));
	return 0;
}
#endif
