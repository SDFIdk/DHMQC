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
#include <stdio.h>
#include <stdlib.h>
#define REAL double
#include "triangle.h"


int *use_triangle(double *xy, int np, int *nt)
{
  struct triangulateio in, out;
  /* Define input points. */
  in.numberofpoints = np;
  in.numberofpointattributes = 0;
  in.pointlist = xy;
  in.pointattributelist=NULL;
  in.pointmarkerlist=NULL;
  in.numberofsegments = 0;
  in.numberofholes = 0;
  in.numberofregions = 0;
  out.pointlist = NULL;
  out.trianglelist=NULL;
  triangulate("zBPNQ", &in, &out, NULL);
  *nt=out.numberoftriangles;
  return out.trianglelist;
}

void get_triangles(int *verts, int *indices, int *out,  int n_indices, int n_trigs){
	int i,j,k,*tmp,bad[3]={-1,-1,-1};
	for(i=0; i<n_indices; i++){
		j=indices[i];
		if (j>=0 && j<n_trigs){
			tmp=verts+3*j;
		}
		else
			tmp=bad;
		for(k=0;k<3;k++){
			out[3*i+k]=tmp[k];
		}
	}
}

/*copy triangle center of masses to out*/
void get_triangle_centers(double *xy, int *triangles, double *out, int n_trigs){
	int i,j,k;
	double mx,my;
	for(i=0; i<n_trigs; i++){
		mx=0;
		my=0;
		for(j=0; j<3; j++){
			k=triangles[3*i+j];
			mx+=xy[2*k];
			my+=xy[2*k+1];
		}
		out[2*i]=mx/3;
		out[2*i+1]=my/3;
	}
}


void free_vertices(int *verts){
	if (verts)
		trifree(verts);
}

#ifdef JONAS_EMIL_STYRER
#include <math.h>
int main(int argc, char **argv){

	double *xy;
	long i,n,m;
	int *verts,nt;
	if (argc<2){
		puts("Input a number <n>...");
		return 1;
	}
	n=atol(argv[1]);
	if (n<3){
		puts("At least 3!");
		return 1;
	}
	xy=malloc(2*n*sizeof(double));
	if (!xy){
		puts("Couldnt alloc...");
		return 1;
	}
	m=(long) (sqrt(n)+1);
	for(i=0; i<n; i++){
		xy[2*i]=i%m;
		xy[2*i+1]=(long) i/m;
	}
	puts("Calling triangle...");
	verts=use_triangle(xy,(int) n, &nt);
	printf("Number of triangles: %d\n",nt); 
	return 0;
	
}
#endif