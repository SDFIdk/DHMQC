@echo off
REM Call with up to 3 args: <path to las/laz file index>  <path to output dir> <path to 2007 pointcloud coverage layer>
if "%2"=="" (
	echo At least two args: "path to las/laz file index" "path to output dir" ["path to 2007 pointcloud tile index"]
	exit /B
)

set TILE_DB=%1
REM we are parsing targs with shlex which will remove bacslahses - so replace those...
set TILE_DB=%TILE_DB:\=/%
set OUTDIR=%2
set TILES_2007=%3
set TOOLS_PATH=%~dp0
set DEV_PATH=%TOOLS_PATH%..
set HERE=%cd%
REM check if tileindex exists
if not exist %TILE_DB% (
    echo Tile index %TILE_DB% does not exist
    exit /B
)
mkdir %OUTDIR%
REM modify below as needed!
cd /D %OUTDIR%
mkdir class_grids
mkdir dems
mkdir diff
mkdir hillshade_dtm
mkdir hillshade_dsm
python %DEV_PATH%\qc_wrap.py -testname class_grid -targs "class_grids -cs 1" -tiles %TILE_DB% -mp 3
gdalbuildvrt class_grid.vrt class_grids\*.tif
gdaladdo -ro --config COMPRESS_OVERVIEW LZW class_grid.vrt 2 4 8 16
REM end class grid
if "%TILES_2007%"=="" goto DEMS
if not exist %TILES_2007% (
	echo Path to 2007 tile index not existing!
	goto DEMS
)
python %DEV_PATH%\qc_wrap.py -testname pointcloud_diff -targs "-cs 4.0 -class 5 -toE -outdir diff" -tiles %TILE_DB% -reftiles %TILES_2007%
gdalbuildvrt diff.vrt diff\*.tif
gdaladdo -ro --config COMPRESS_OVERVIEW LZW diff.vrt  2 4 8 16
REM end diff

:DEMS
python %DEV_PATH%\qc_wrap.py -testname dem_gen_new -tiles %TILE_DB% -targs "%TILE_DB% dems -dtm -dsm -nowarp -overwrite"  
REM start dtm hillshade - cd to outdir to avoid fuck up of relative paths across drives.
del dtm.sqlite
del dsm.sqlite
python %DEV_PATH%\tile_coverage.py create dems tif dtm.sqlite --fpat dtm
python %DEV_PATH%\tile_coverage.py create dems tif dsm.sqlite --fpat dsm

python %DEV_PATH%\qc_wrap.py -testname hillshade -tiles dtm.sqlite -targs "hillshade_dtm -tiledb dtm.sqlite" -mp 3
python %DEV_PATH%\qc_wrap.py -testname hillshade -tiles dsm.sqlite -targs "hillshade_dsm -tiledb dsm.sqlite" -mp 3
gdalbuildvrt dtm_shade.vrt hillshade_dtm\*.tif
gdalbuildvrt dsm_shade.vrt  hillshade_dsm\*.tif
REM start building overviews
set cmd1="gdaladdo -ro --config COMPRESS_OVERVIEW LZW -r gauss dtm_shade.vrt 4 8 16 32"
set cmd2="gdaladdo -ro --config COMPRESS_OVERVIEW LZW -r gauss dsm_shade.vrt 4 8 16 32"
python %DEV_PATH%\rip.py %cmd1% %cmd2%
cd /D %HERE%

