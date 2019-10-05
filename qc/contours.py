# -*- coding: utf-8 -*-
import os,sys
import shutil
from argparse import ArgumentParser
import subprocess
import tempfile
import time
import datetime
import random

from osgeo import gdal
from osgeo import ogr
from osgeo import osr

import numpy as np
from scipy.signal import convolve2d

from . import dhmqc_constants as constants


gdal.UseExceptions()
ogr.UseExceptions()


# Can be called from a project file containing following statements: 
#TESTNAME="contours"
#INPUT_TILE_CONNECTION=r"dtm_bro.sqlite"
#TARGS=[r"""dbname='dbname' host='IP-nummer' port='5432' user='user' password='passw'""", 
#r"P:\ath\to\dtm_without_bridges.vrt", 
#"-schema", "kurvtest"]
#print (TARGS)


extent = 200
target_resolution = 1.6 # værdier til generalisering af kurver
interval = 0.5

progname=os.path.basename(__file__)
parser=ArgumentParser(description="calculate a 1km contour file with 50 cm interval",prog=progname)
parser.add_argument("tilename", help="Tilename to calculate (eg 1km_6666_666)")
parser.add_argument("dbout", help="sqlite file for output")
parser.add_argument("dtm_path", help="path to terrain file (vrt or large tiff)")
parser.add_argument("-schema", help="if using a postgis db it may be beneficial to add a schema name")


buf = float(extent)


# 1km grid kurveberegning	
#Get the extent from a tilename (1km_NNNN_EEE). Can return a wkt)
def create1km(tilename, buf, return_wkt=False):
	#might throw an exception - wrap in try, except...
	tile_size = 1000
	N,E=tilename.split("_")[1:3]
	N=int(N)
	E=int(E)
	xt=(E*tile_size-buf,N*tile_size-buf,(E+1)*tile_size+buf,(N+1)*tile_size+buf)
	if return_wkt:
		wkt="POLYGON(("
		for dx,dy in ((0,0),(0,1),(1,1),(1,0)):
			wkt+="{0:.2f} {1:.2f},".format(xt[2*dx],xt[2*dy+1])
		wkt+="{0:.2f} {1:.2f}))".format(xt[0],xt[1])
		return wkt
	#x1,y1,x2,y2 - fits into the array_geometry.bbox_to_polygon method
	return xt
	

# 10km grid kurveberegning
# Get the extent from a tilename (10km_NNN_EEE). Can return a wkt)
def create10km(tilename, buf, return_wkt=False):
	#might throw an exception - wrap in try, except...
	tile_size = 10000
	N,E=tilename.split("_")[1:3]
	N=int(N)
	E=int(E)
	xt=(E*tile_size-buf,N*tile_size-buf,(E+1)*tile_size+buf,(N+1)*tile_size+buf)
	if return_wkt:
		wkt="POLYGON(("
		for dx,dy in ((0,0),(0,1),(1,1),(1,0)):
			wkt+="{0:.2f} {1:.2f},".format(xt[2*dx],xt[2*dy+1])
		wkt+="{0:.2f} {1:.2f}))".format(xt[0],xt[1])
		return wkt
	#x1,y1,x2,y2 - fits into the array_geometry.bbox_to_polygon method
	return xt

	
# Gauss filter til brug i beregning - NIKS PILLE
def gauss_smooth_geotiff(input_filename, output_filename, kernel_width, georef_stddev):
	"""
	Perform Gaussian smoothing on a one-band GeoTIFF file.
	
	Args:
		input_filename: Filename of the input GeoTIFF file.
		output_filename: Filename of the output GeoTIFF file (the smoothed data).
		kernel_width: (Integer) size in pixels of the Gaussian kernel.
		georef_stddev: Standard deviation of the Gaussian distribution, in georeferenced units.
	"""
	
	kernel_x, kernel_y = np.meshgrid(np.arange(0, kernel_width) + 0.5 - 0.5*kernel_width, 0.5*kernel_width - np.arange(0, kernel_width) - 0.5)
	
	input_datasrc = gdal.Open(input_filename)
	input_band = input_datasrc.GetRasterBand(1)
	input_geo_transform = input_datasrc.GetGeoTransform()
	input_projection = input_datasrc.GetProjection()
	input_nodata_value = input_band.GetNoDataValue()
	input_array_data_raw = input_band.ReadAsArray()
	
	# Prepare Gauss kernel
	kernel_georef_x = input_geo_transform[1] * kernel_x
	kernel_georef_y = -input_geo_transform[5] * kernel_y
	kernel_georef_r = np.sqrt(kernel_georef_x**2 + kernel_georef_y**2)
	kernel_georef_gauss = 1./np.sqrt(2*np.pi*georef_stddev**2) * np.exp(-kernel_georef_r**2/(2*georef_stddev**2))
	
	# Perform convolution on data and mask
	input_array_data = input_array_data_raw.copy()
	input_array_data[input_array_data_raw == input_nodata_value] = 0.0 #avoid propagating NaNs
	input_array_mask = (input_array_data_raw != input_nodata_value).astype(np.float)
	convolved_weights = convolve2d(input_array_mask, kernel_georef_gauss, mode='same')
	convolved_array_data = convolve2d(input_array_data, kernel_georef_gauss, mode='same')
	output_array_data = np.full_like(input_array_data, np.nan)
	
	# Normalize each pixel from the convolved data based on the convolved mask
	output_mask = convolved_weights != 0.0
	output_array_data[output_mask] = convolved_array_data[output_mask] / convolved_weights[output_mask]
	
	num_output_rows, num_output_cols = output_array_data.shape

	output_driver = gdal.GetDriverByName("GTiff")
	output_datasrc = output_driver.Create(output_filename, num_output_cols, num_output_rows, 1, gdal.GDT_Float32)
	output_datasrc.SetProjection(input_projection)
	output_datasrc.SetGeoTransform(input_geo_transform)
	output_band = output_datasrc.GetRasterBand(1)
	output_band.SetNoDataValue(input_nodata_value)
	output_band.WriteArray(output_array_data)
	output_band.FlushCache()

	
		
def main(args):
	pargs=parser.parse_args(args[1:])
	dtm_path = pargs.dtm_path
	tilename = constants.get_tilename(pargs.tilename)
	
	blindspot = open(os.devnull, 'w')

	#obsolete checks from old code. Kept it here anyway
	if  tilename[0:3] == '1km':
		create1km(tilename, buf)
		bbox = create1km(tilename, buf)
		bbox_tile = create1km(tilename, buf=0)

	elif tilename[0:4] == '10km':
		create10km(tilename)
		bbox = create10km(tilename, buf)
		bbox_tile = create10km(tilename, buf=0)

	# Temporary library for calculation
	temp_dir = tempfile.mkdtemp()

	bbox_kmname = '%s %s %s %s' %(bbox_tile[0], bbox_tile[1], bbox_tile[2], bbox_tile[3])
	bbox_grid = '%s %s %s %s' %(bbox[0], bbox[2], bbox[1], bbox[3])
	bbox_te = '%s %s %s %s' %(bbox[0], bbox[1], bbox[2], bbox[3])

	"""
	Kurveberegning
	"""
	
#	print ("-----cutting dtm hard-----\n")
	temp_dtm_hard = os.path.join(temp_dir,'temp_dtm_hard.tif')
	exestr = 'gdalwarp -of GTiff -tr %s %s -tap -dstnodata -9999 -r bilinear -s_srs epsg:25832 -t_srs epsg:25832 -te %s %s %s -q' %(target_resolution, target_resolution, bbox_te, dtm_path, temp_dtm_hard)
	subprocess.call(exestr, shell=True)
#	print ("\n-----Finished cutting-----\n\n")
	
#	print ("-----running gauss filter-----\n")
	temp_dtm_gauss = os.path.join(temp_dir,'gauss.tif')
	gauss_smooth_geotiff(temp_dtm_hard, temp_dtm_gauss, 3, 12)
#	print ("\n-----gauss filter complete-----\n\n")

#	print ("-----calculate roughness index-----\n")
	temp_dtm_rough = os.path.join(temp_dir,'temp_dtm_rough.tif')
	exestr = 'gdaldem roughness -of GTiff %s %s -q' %(temp_dtm_hard, temp_dtm_rough)
	subprocess.call(exestr, shell=True)
#	print ("\n-----Finished roughness calc-----\n\n")
		
#	print ("-----joining dtm after roughness-----\n")
	temp_dtm_join = os.path.join(temp_dir,'temp_dtm_join.tif')
	exestr = 'gdal_calc -A %s -B %s -C %s --calc="(A<5)*C+(A>=5)*(A<=10)*((((A-5.0)/(10.0-5))*B)+(1-((A-5.0)/(10.0-5)))*C)+(A>10)*B" --outfile=%s --NoDataValue=-9999 --quiet' %(temp_dtm_rough, temp_dtm_hard, temp_dtm_gauss, temp_dtm_join)
	subprocess.check_call(exestr, shell=True)
#	print ("\n-----Finished cutting-----\n\n")

#Following has been commented out - for using a land polygon. Not implemented for now.
	# rasterizing "GeoDK landpolygon", to cut nodata outside coastal line
#	print ('geodk landpolygon til raster')
#	temp_landraster = os.path.join(temp_dir,'temp_landraster.tif')
#	exestr = 'gdal_rasterize -tr %s %s -burn 1 -init 0 -a_nodata -9999 -te %s -ot Float32 -of GTiff %s %s' %(target_resolution, target_resolution, bbox_te, landpolygon, temp_landraster)
#	subprocess.call(exestr, shell=True)

#	print ("-----cutting landmass-----\n")
#	temp_dtm_kun_land = os.path.join(temp_dir,'temp_dtm_kun_land.tif')
#	exestr = 'gdal_calc -A %s -B %s --calc="(A*B)" --outfile=%s --NoDataValue=-9999' %(temp_dtm_join, temp_landraster, temp_dtm_kun_land)
#	subprocess.call(exestr, shell=True)
#	print ("\n-----Finished cutting-----\n\n")
	
#	print ("-----Contouring------\n")
	temp_contours = os.path.join(temp_dir,'temp_contours.shp')
	exestr= 'gdal_contour -a kote -i %s -f "ESRI Shapefile" %s %s' %(interval, temp_dtm_join, temp_contours)
	subprocess.call(exestr, shell=True, stdout=blindspot)
#	print ("\n-----Contouring finished------\n\n")
	
	exestr = 'ogrinfo %s -sql "alter table temp_contours add column km_name string" -q' %(temp_contours)
	subprocess.call(exestr, shell=True)
#	print ("-----km_name added to table------\n")

	exestr = 'ogrinfo %s -dialect SQLite -sql "update temp_contours set km_name=\'%s\' "  -q' %(temp_contours, tilename)
	subprocess.call(exestr, shell=True)
#	print ("-----km_name update------\n")

	
	print ("-----inserting to db------\n")

	# Ekstrempunkter og kurveberegning til database. 
	"""
	Skema skal eksistere i forvejen. Tabel behøver ikke.
	"""
	#if dbout is an sqlite connection it will be generated. Works with a MP set low. 
	if '.sqlite' in pargs.dbout: 
		if not os.path.isfile(pargs.dbout):
			time.sleep(random.randint(0,20)) 
			exestr = """ogr2ogr -f SQLite -a_srs epsg:25832 -dsco SPATIALITE=YES %s %s -lco SPATIAL_INDEX=NO -nln contours -clipdst %s -nlt PROMOTE_TO_MULTI -skipfailures""" %(pargs.dbout,temp_contours,bbox_kmname) 		
			if os.path.isfile(pargs.dbout):
				exestr = """ogr2ogr -f SQLite -a_srs epsg:25832 -append %s %s -nln contours -clipdst %s -nlt PROMOTE_TO_MULTI -skipfailures""" %(pargs.dbout, temp_contours, bbox_kmname)
		else:   	
			exestr = """ogr2ogr -f SQLite -a_srs epsg:25832 -append %s %s -nln contours -clipdst %s -nlt PROMOTE_TO_MULTI -skipfailures""" %(pargs.dbout, temp_contours, bbox_kmname)
		subprocess.call(exestr, shell=True, stdout=blindspot)
	else: 
		#if dbout is NOT sqlite, we will write to the postgis db, also using the -schema attrib
		exestr = """ogr2ogr  -f PostgreSQL PG:"%s" %s -nln %s.f_contours -nlt PROMOTE_TO_MULTI -append -clipdst %s""" %(pargs.dbout, temp_contours, pargs.schema, bbox_kmname)
		subprocess.call(exestr, shell=True)
	
	#print ("\n-----All finished-----\n\n\n\n\n")
	
	shutil.rmtree(temp_dir)	

if __name__=="__main__":
	main(sys.argv)

