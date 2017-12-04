import os
import time

import qc
from qc.db import report

from qc.thatsDEM import triangle
from qc.thatsDEM import array_geometry
from qc.thatsDEM import pointcloud

import qc.density_check
import qc.z_precision_roads
import qc.roof_ridge_strip
import qc.spike_check
import qc.z_accuracy
import qc.classification_check
import qc.count_classes
import qc.las2polygons
import qc.las2polygons
import qc.road_delta_check
import qc.roof_ridge_alignment
import qc.xy_accuracy_buildings
import qc.xy_precision_buildings
import qc.wobbly_water
import qc.dvr90_wrapper
import qc.pc_repair_man

HERE = os.path.dirname(__file__)
DEMO_FOLDER = os.path.join(HERE, 'demo')
LAS_DEMO = os.path.join(DEMO_FOLDER, '1km_6173_632.las')
WATER_DEMO = os.path.join(DEMO_FOLDER, 'water_1km_6173_632.geojson')
ROAD_DEMO = os.path.join(DEMO_FOLDER, 'roads_1km_6173_632.geojson')
BUILDING_DEMO = os.path.join(DEMO_FOLDER, 'build_1km_6173_632.geojson')
DEMO_FILES = [LAS_DEMO, WATER_DEMO, ROAD_DEMO, BUILDING_DEMO]
OUTDIR = os.path.join(HERE, 'test_output')
OUTPUT_DS = os.path.join(OUTDIR, 'test_suite.sqlite')

def setup_module():
    '''Initual setup needed before tests can run.'''
    ds = report.create_local_datasource(OUTPUT_DS)
    report.set_datasource(ds)
    report.set_run_id(int(time.time()))  # a time stamp

def teardown_module():
    '''Clean up'''
    # we need to close the connection to the sqlite db before it can be removed
    report.close_datasource()
    os.remove(OUTPUT_DS)

class TestThatsDEM:
    '''
    Test modules in the thatsDEM package.

    The unit tests raises AssertionError's upoin failure, hence it is enough
    to just call the test functions here.
    '''

    def test_pointcloud(self):
        pointcloud.unit_test(LAS_DEMO)

    def test_array_geometry(self):
        array_geometry.unit_test()

    def test_triangle(self):
        triangle.unit_test()

class TestKernels:
    '''
    Test QC kernels.

    Most tests in this class are dumb in the sense that they only test if a
    given function runs without failing - the output is not checked!

    Some main functions uses return codes, others don't. It's a mess, really,
    but here we are trying to read return code from the functions that uses
    them. For functions without return codes we rely on exceptions being raised
    when errors occur.
    '''

    def test_density_check(self):
        rc = qc.density_check.main(('density_check', LAS_DEMO, WATER_DEMO))
        assert rc == 0

    def test_z_precision_roads(self):
        qc.z_precision_roads.main(('z_precision_roads', LAS_DEMO, ROAD_DEMO))

    def test_roof_ridge_strip(self):
        qc.roof_ridge_strip.main(
            ('roof_ridge_strip', LAS_DEMO, BUILDING_DEMO, '-search_factor', '1.1', '-use_all')
        )

    def test_spike_check(self):
        qc.spike_check.main(('spike_check', LAS_DEMO, '-zlim', '0.08', '-slope', '8'))

    def test_z_accuracy(self):
        qc.z_accuracy.main(('z_accuracy', LAS_DEMO, ROAD_DEMO, '-lines', '-toE')),

    def test_classification_check(self):
        qc.classification_check.main(('classification_check', LAS_DEMO, BUILDING_DEMO, '-below_poly', '-toE'))

    def test_count_classes(self):
        qc.count_classes.main(('count_classes', LAS_DEMO))

    def test_las2polygons(self):
        rc = qc.las2polygons.main(('las2polygons', LAS_DEMO))
        assert rc == 0

    def test_las2polygons2(self):
        rc = qc.las2polygons.main(('las2polygons',LAS_DEMO, '-height', '300'))
        assert rc == 0

    def test_road_delta_check(self):
        qc.road_delta_check.main(('road_delta_check', LAS_DEMO, ROAD_DEMO, '-zlim', '0.1'))

    def test_roof_ridge_alignment(self):
        qc.roof_ridge_alignment.main((
            'roof_ridge_alignment', LAS_DEMO, BUILDING_DEMO,
            '-use_all', '-search_factor', '1.1'))

    def test_xy_accuracy_buildings(self):
        qc.xy_accuracy_buildings.main(('xy_accuracy_buildings', LAS_DEMO, BUILDING_DEMO))

    def test_xy_precision_buildings(self):
        qc.xy_precision_buildings.main(('xy_precision_buildings', LAS_DEMO, BUILDING_DEMO))

    def test_wobbly_water(self):
        rc = qc.wobbly_water.main(('wobbly_water', LAS_DEMO))
        assert rc == 0

    def test_dvr90_wrapper(self):
        rc = qc.dvr90_wrapper.main(('dvr90_wrapper', LAS_DEMO, OUTDIR))
        assert rc == 0

    def test_pc_repair_man(self):
        rc = qc.pc_repair_man.main(('pc_repair_man', LAS_DEMO, OUTDIR, '-olaz'))
        assert rc == 0

