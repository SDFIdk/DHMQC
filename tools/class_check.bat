REM Call with  3 args: <TILE_DB>  <SCHEMA> <RUNID>
if "%3"=="" (
	echo At least 3 args: "path to las_coverage.sqlite" "dbschema" "runid"
	exit /B
)
REM start of classification batch tests (not producing grids)
set TILE_DB=%1
set SCHEMA=%2
set RUNID=%3
set TOOLS_PATH=%~dp0
set DEV_PATH=%TOOLS_PATH%..
echo "Calling script to set reference data connections - must define REFCON, HOUSES, LAKES and ROADS"
call reflayers.bat

python %DEV_PATH%\qc_wrap.py -testname spike_check -schema %SCHEMA% -targs "-zlim 0.25" -tiles %TILE_DB% -runid %RUNID%
python %DEV_PATH%\qc_wrap.py -testname count_classes -schema %SCHEMA% -tiles %TILE_DB% -runid %RUNID%
python %DEV_PATH%\qc_wrap.py -testname classification_check -schema %SCHEMA% -tiles %TILE_DB% -runid %RUNID% -refcon %REFCON% -targs "-type building -layersql %HOUSES%"
python %DEV_PATH%\qc_wrap.py -testname classification_check -schema %SCHEMA% -tiles %TILE_DB% -runid %RUNID% -refcon %REFCON% -targs "-type lake -layersql %LAKES%"
python %DEV_PATH%\qc_wrap.py  templates\args_delta_roads.py -schema %SCHEMA% -tiles %TILE_DB% -runid %RUNID% -refcon %REFCON% 
python %DEV_PATH%\qc_wrap.py -testname classification_check -schema %SCHEMA% -tiles %TILE_DB% -runid %RUNID% -refcon %REFCON% -targs "-layersql %HOUSES% -below_poly -toE" 
python %DEV_PATH%\qc_wrap.py -testname las2polygons -schema %SCHEMA% -tiles %TILE_DB% -runid %RUNID% 