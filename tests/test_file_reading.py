'''
Test basic reading with laspy.

Some versions of lazrs (0.4.1 is known to) may choke on the compression
scheme of certain LAZ files. Test that we are able to read one of those.
'''

import laspy

from . import conftest

def test_read_las():
    _ = laspy.read(conftest.LAS_DEMO)

def test_read_laz():
    _ = laspy.read(conftest.LAZ_DEMO)