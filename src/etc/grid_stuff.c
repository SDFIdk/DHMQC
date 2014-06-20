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
* Grid should always have a nd_val. If there is no - it's up to the caller to supply one, which is not a regular grid_val, e.g. min(grid)-999...
* CONSIDER making this just use thokns esrigrid.h....
*/
DLL_EXPORT void wrap_bilin(double *grid, double *xy, double *out, double *geo_ref, double nd_val, int nrows, int ncols, int npoints){
	int i,j,k;
	double x,y,dx,dy,grid_vals[4],*g; 
	for(k=0; k<npoints; k++){
		/*find the 4 centers that we need*/
		if (geo_ref){
			x=(xy[2*k]-geo_ref[0])/geo_ref[1];
			y=(geo_ref[2]-xy[2*k+1])/geo_ref[3];
		}
		else{
			x=xy[2*k];
			y=xy[2*k+1];
		}
		i=(int) y;
		j=(int) x;
		out[k]=nd_val;
		/*ok - so the lower and right boundary is not included... too bad man*/
		if (i<0 ||  j<0 || i>(nrows-2) || j>(ncols-2)){
			continue;
		}
		dx=x-j;
		dy=y-i;
		/*clock-wise filling of values and no_data check*/
		g=grid+(ncols*i+j);
		if (nd_val==(grid_vals[0]=*g)){
			continue;
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
		out[k]=grid_vals[0]+dx*(grid_vals[1]-grid_vals[0])+dy*(grid_vals[3]-grid_vals[0])+dx*dy*(grid_vals[0]-grid_vals[1]-grid_vals[3]+grid_vals[2]);
	}		
}