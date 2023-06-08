import qc
from qc.db import report

import pytest

import os
import time

HERE = os.path.split(os.path.dirname(__file__))[0]
DEMO_FOLDER = os.path.join(HERE, 'demo')
LAS_DEMO = os.path.join(DEMO_FOLDER, '1km_6173_632.las')
LAZ_DEMO = os.path.join(DEMO_FOLDER, '1km_6076_548.laz')
WATER_DEMO = os.path.join(DEMO_FOLDER, 'water_1km_6173_632.geojson')
ROAD_DEMO = os.path.join(DEMO_FOLDER, 'roads_1km_6173_632.geojson')
BUILDING_DEMO = os.path.join(DEMO_FOLDER, 'build_1km_6173_632.geojson')
DEMO_FILES = [LAS_DEMO, WATER_DEMO, ROAD_DEMO, BUILDING_DEMO]

@pytest.fixture
def outdir(tmpdir):
    return tmpdir

@pytest.fixture
def output_ds(outdir):
    ds_path = outdir / 'test_suite.sqlite'
    ds = report.create_local_datasource(str(ds_path))
    report.set_datasource(ds)
    report.set_run_id(int(time.time()))  # a time stamp

    yield ds_path

    report.close_datasource()
