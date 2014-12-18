#include <stdlib.h>
#ifdef _MSC_VER
#define DLL_EXPORT __declspec(dllexport)
#else
#define DLL_EXPORT  
#endif
/*simple bilnear interpolation here:
* If geo_ref is NULL, we assume that xy is already in array coordinates,
* If geo_ref is NOT NULL it should be an array of len 4: x1,cx,y2,cy - with (x1,y2) being the center of the upper left 'pixel', i.e. the location of the upper left grid point, i.e.:
* x1=xul_center, y2=yul_center
* This is unlike the usual GDAL-style convention (pixel corner), since we primarily focus on interpolation in 'geoid' grids... 
* We consider the values of the grid array as representing the grid values at the 'centers of the pixels'.
* Simplistic and predictable approach: If upper left corner is no-data, output will be no-data. Otherwise no-data is filled clock-wise.
* This means that no-data will 'spread' in the south-west direction... However exact cell centers should be interpolateable with no no-data spreading ;-)
* Grid should always have a nd_val. If there is none - it's up to the caller to supply one, which is not a regular grid_val, e.g. min(grid)-999...
* CONSIDER making this just use thokns esrigrid.h....
*/
static double simple_bilin(double *grid, double x, double y, double *geo_ref, double nd_val, int nrows, int ncols);

static double simple_bilin(double *grid, double x, double y, double *geo_ref, double nd_val, int nrows, int ncols){
	int i,j;
	double dx,dy,grid_vals[4],*g;
	if (geo_ref){
		x=(x-geo_ref[0])/geo_ref[1];
		y=(geo_ref[2]-y)/geo_ref[3];
	}
	i=(int) y;
	j=(int) x;
	/*ok - so the lower and right boundary is not included... too bad man*/
	if (i<0 ||  j<0 || i>(nrows-2) || j>(ncols-2)){
			return nd_val;
	}
	dx=x-j;
	dy=y-i;
	/*clock-wise filling of values and no_data check*/
	g=grid+(ncols*i+j);
	if (nd_val==(grid_vals[0]=*g)){
			return nd_val;
	}
	if (nd_val==(grid_vals[1]=*(g+1))){
		grid_vals[1]=grid_vals[0];
	}
	if (nd_val==(grid_vals[2]=*(g+1+ncols))){
		grid_vals[2]=grid_vals[1];
	}
	if (nd_val==(grid_vals[3]=*(g+ncols))){
		grid_vals[3]=grid_vals[2];
	}
	/*possibly the compiler will be able to optimize this expression...*/
	return (grid_vals[0]+dx*(grid_vals[1]-grid_vals[0])+dy*(grid_vals[3]-grid_vals[0])+dx*dy*(grid_vals[0]-grid_vals[1]-grid_vals[3]+grid_vals[2]));
}

DLL_EXPORT void wrap_bilin(double *grid, double *xy, double *out, double *geo_ref, double nd_val, int nrows, int ncols, int npoints){
	int k;
	for(k=0; k<npoints; k++){
		/*find the 4 centers that we need*/
		out[k]=simple_bilin(grid,xy[2*k],xy[2*k+1],geo_ref,nd_val,nrows,ncols);
		
	}		
}

/*both grid1 and grid2 must be georeferenced like described above*/
DLL_EXPORT void resample_grid(double *grid, double *out, double *geo_ref, double *geo_ref_out, double nd_val, int nrows, int ncols, int nrows_out, int ncols_out){
	int i,j;
	double x,y;
	for(i=0;i<nrows_out; i++){
		for(j=0;j<ncols_out; j++){
			x=geo_ref_out[0]+j*geo_ref_out[1]; /* geo_ref[0] refers to pixel 'center' - POINT interpretation...*/
			y=geo_ref_out[2]-i*geo_ref_out[3];
			out[i*ncols_out+j]=simple_bilin(grid,x,y,geo_ref,nd_val,nrows,ncols);
		}
	}
}


/* assign most frequent value in each cell to output grid */
DLL_EXPORT void grid_most_frequent_value(int *sorted_indices, int *values, int *out, int vmin,int vmax,int nd_val, int n){
	int i,j,*count,range,cell,current_cell,val;
	range=vmax-vmin+1;
	count=calloc(range,sizeof(int));
	current_cell=sorted_indices[0];
	for(i=0; i<n; i++){
		cell=sorted_indices[i];
		if (cell>current_cell){
			/*assign value and move on*/
			int most_frequent=nd_val,max_count=-1; /*-1 will be a no-data value*/
			for(j=0;j<range;j++){
				if (count[j]>max_count){
					most_frequent=j;
					max_count=count[j];
				}
				count[j]=0; /*reset*/
			}
			out[current_cell]=most_frequent+vmin;
			current_cell=cell;
		}
		else{
			val=values[i]-vmin;
			if (val>=0 && val<range)
				count[val]++;
		}
		
	}
	free(count);
}


