'''
Test QC kernels.

Most tests in this class are dumb in the sense that they only test if a
given function runs without failing - the output is not checked!

Some main functions uses return codes, others don't. It's a mess, really,
but here we are trying to read return code from the functions that uses
them. For functions without return codes we rely on exceptions being raised
when errors occur.
'''

from . import conftest
# from .conftest import LAS_DEMO, WATER_DEMO, ROAD_DEMO, BUILDING_DEMO, OUTDIR

# import qc
# from qc.db import report

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

def test_density_check(output_ds):
    rc = qc.density_check.main(('density_check', conftest.LAS_DEMO, conftest.WATER_DEMO))
    assert rc == 0

def test_z_precision_roads(output_ds):
    qc.z_precision_roads.main(('z_precision_roads', conftest.LAS_DEMO, conftest.ROAD_DEMO))

def test_roof_ridge_strip(output_ds):
    qc.roof_ridge_strip.main(
        ('roof_ridge_strip', conftest.LAS_DEMO, conftest.BUILDING_DEMO, '-search_factor', '1.1', '-use_all')
    )

def test_spike_check(output_ds):
    qc.spike_check.main(('spike_check', conftest.LAS_DEMO, '-zlim', '0.08', '-slope', '8'))

def test_z_accuracy(output_ds):
    qc.z_accuracy.main(('z_accuracy', conftest.LAS_DEMO, conftest.ROAD_DEMO, '-lines', '-toE')),

def test_classification_check(output_ds):
    qc.classification_check.main(('classification_check', conftest.LAS_DEMO, conftest.BUILDING_DEMO, '-below_poly', '-toE'))

def test_count_classes(output_ds):
    qc.count_classes.main(('count_classes', conftest.LAS_DEMO))

def test_las2polygons(output_ds):
    rc = qc.las2polygons.main(('las2polygons', conftest.LAS_DEMO))
    assert rc == 0

def test_las2polygons2(output_ds):
    rc = qc.las2polygons.main(('las2polygons', conftest.LAS_DEMO, '-height', '300'))
    assert rc == 0

def test_road_delta_check(output_ds):
    qc.road_delta_check.main(('road_delta_check', conftest.LAS_DEMO, conftest.ROAD_DEMO, '-zlim', '0.1'))

def test_roof_ridge_alignment(output_ds):
    qc.roof_ridge_alignment.main((
        'roof_ridge_alignment', conftest.LAS_DEMO, conftest.BUILDING_DEMO,
        '-use_all', '-search_factor', '1.1'))

def test_xy_accuracy_buildings(output_ds):
    qc.xy_accuracy_buildings.main(('xy_accuracy_buildings', conftest.LAS_DEMO, conftest.BUILDING_DEMO))

def test_xy_precision_buildings(output_ds):
    qc.xy_precision_buildings.main(('xy_precision_buildings', conftest.LAS_DEMO, conftest.BUILDING_DEMO))

def test_wobbly_water(output_ds):
    rc = qc.wobbly_water.main(('wobbly_water', conftest.LAS_DEMO))
    assert rc == 0

def test_dvr90_wrapper(outdir, output_ds):
    rc = qc.dvr90_wrapper.main(('dvr90_wrapper', conftest.LAS_DEMO, str(outdir)))
    assert rc == 0

