REM Call with up to 3 args: <path to las files> <path to output dir> <path to 2007 pointcloud coverage layer>
if "%2"=="" (
	echo At least two args: "path to las files" "path to output dir" ["path to 2007 pointcloud tile coverage layer"]
	exit /B
)
set TILE_PATH=%1
set OUTDIR=%2
set TILES_2007=%3
set TOOLS_PATH=%~dp0
set DEV_PATH=%TOOLS_PATH%..
set HERE=%cd%
REM modify below as needed!

set TILE_DB=las_coverage.sqlite
mkdir %OUTDIR%
cd /D %OUTDIR%
mkdir class_grids
mkdir dems
mkdir diff
mkdir hill_dtm
mkdir hill_dsm
del %TILE_DB%
echo "Creating tile db %TILE_DB% from path %TILE_PATH%, grids in %OUTDIR%"
python %DEV_PATH%\tile_coverage.py create %TILE_PATH% las %TILE_DB%
python %DEV_PATH%\qc_wrap.py -testname class_grid -targs "class_grids -cs 1" -tiles %TILE_DB% -mp 5
gdalbuildvrt class_grid.vrt class_grids\*.tif
gdaladdo -ro --config COMPRESS_OVERVIEW LZW class_grid.vrt 2 4 8 16
REM end class grid
if "%TILES_2007%"=="" goto DEMS
if not exist %TILES_2007% (
	echo Path to 2007 las tiles not existing!
	goto DEMS
)
python %DEV_PATH%\qc_wrap.py -testname pointcloud_diff -targs "-cs 4.0 -class 5 -toE -outdir diff" -tiles %TILE_DB% -reftiles %TILES_2007%
gdalbuildvrt diff.vrt diff\*.tif
gdaladdo -ro --config COMPRESS_OVERVIEW LZW diff.vrt  2 4 8 16
REM end diff
REM for this to work - use / slashes in path to tile_db!
:DEMS
python %DEV_PATH%\qc_wrap.py -testname dem_gen_new -tiles %TILE_DB% -targs "null dems -dtm -dsm -nowarp -tiledb %TILE_DB%"  
REM start dtm hillshade - cd to outdir to avoid fuck up of relative paths across drives.
python %DEV_PATH%\tile_coverage.py create dems tif dtm.sqlite --fpat dtm
python %DEV_PATH%\tile_coverage.py create dems tif dsm.sqlite --fpat dsm
mkdir hillshade_dtm
mkdir hillshade_dsm
python %DEV_PATH%\qc_wrap.py -testname hillshade -tiles dtm.sqlite -targs "hillshade_dtm -tiledb dtm.sqlite" -mp 5
python %DEV_PATH%\qc_wrap.py -testname hillshade -tiles dsm.sqlite -targs "hillshade_dsm -tiledb dsm.sqlite" -mp 5
gdalbuildvrt dtm_shade.vrt hillshade_dtm\*.tif
gdalbuildvrt dsm_shade.vrt  hillshade_dsm\*.tif
REM start building overviews
set cmd1="gdaladdo -ro --config COMPRESS_OVERVIEW LZW -r gauss dtm_shade.vrt 4 8 16 32"
set cmd2="gdaladdo -ro --config COMPRESS_OVERVIEW LZW -r gauss dsm_shade.vrt 4 8 16 32"
python %DEV_PATH%\rip.py %cmd1% %cmd2%
cd /D %HERE%

