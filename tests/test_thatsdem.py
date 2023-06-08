'''
Test modules in the thatsDEM package.

The unit tests raises AssertionError's upoin failure, hence it is enough
to just call the test functions here.
'''

from qc.thatsDEM import triangle
from qc.thatsDEM import array_geometry
from qc.thatsDEM import pointcloud

from . import conftest

def test_pointcloud():
    pointcloud.unit_test(conftest.LAS_DEMO)

def test_array_geometry():
    array_geometry.unit_test()

def test_triangle():
    triangle.unit_test()