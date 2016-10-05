# Copyright (c) 2015-2016, Danish Geodata Agency <gst@gst.dk>
# Copyright (c) 2016, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

'''
grid_gpstime.py

Create a raster grid of gps time from a pointcloud.
'''

from __future__ import print_function

import os
import sys
import time
from datetime import datetime, timedelta

import numpy as np
import laspy

import dhmqc_constants as constants
from utils.osutils import ArgumentParser
from db import report

PROGNAME = os.path.basename(__file__).replace(".pyc", ".py")

parser = ArgumentParser(
    description="Report date statistics to database.",
    prog=PROGNAME)
parser.add_argument("las_file", help="Input las tile.")

db_group = parser.add_mutually_exclusive_group()
db_group.add_argument(
    "-use_local",
    action="store_true",
    help="Force use of local database for reporting.")

db_group.add_argument(
    "-schema",
    help="Specify schema for PostGis db.")

def usage():
    '''
    Print usage
    '''
    parser.print_help()

def to_gpstime(timestamp):
    '''
    Convert datetime to gps time. Leap seconds are ignored.

    timestamp:      datetime.datetime object

    returns gps time (float)
    '''

    return (timestamp - datetime(1980, 1, 6)).total_seconds() - 10**9

def to_datetime(gps_time):
    '''
    Convert gps time to UTC time. Leap seconds are ignored.

    Consult the LAS specification to get an explanation of how
    the GPS time relates to UTC dates.

    gps_time:       float with gps time.

    returns a datetime.datetime object
    '''

    return datetime(1980, 1, 6) + timedelta(seconds=gps_time + 10**9)

def find_unique_days(gps_times):
    '''
    Find unique days in a list of GPS times.

    Unique days are found by creating a histogram of all the GPS times in
    the input list. The histogram bins are carefully constructed such that
    there is a bin for each day in the time period the data spans.
    Every non-zero bin in the histogram equals a unique day where data has
    been acquired.

    Input:
    ------
    gps_times:      numpy array with gps-times. Usually from laspy.

    Returns:
    -------
    list of datetime objects
    '''
    # find extremas
    min_dt = to_datetime(np.min(gps_times))
    max_dt = to_datetime(np.max(gps_times))
    first_day = min_dt.date()
    last_day = max_dt.date() + timedelta(days=1)

    # Calculate histogram of gps-times. Super fast way to group timestamps.
    # One bin per day. Usually most bins will be empty.
    # Non-empty bins corresponds to days were data was collected.
    limits = (
        to_gpstime(datetime.combine(first_day, datetime.min.time())),
        to_gpstime(datetime.combine(last_day, datetime.min.time()))
    )

    n_bins = (last_day - first_day).days
    hist, bins = np.histogram(gps_times, bins=n_bins, range=limits)

    I = np.where(hist > 0)
    datetimes = [to_datetime(timestamp) for timestamp in bins[I]]

    return datetimes


def main(args):
    '''
    Main function
    '''
    try:
        pargs = parser.parse_args(args[1:])
    except TypeError, error_msg:
        print(str(error_msg))
        return 1

    kmname = constants.get_tilename(pargs.las_file)
    wkt = constants.tilename_to_extent(kmname, return_wkt=True)
    print("Running %s on block: %s, %s" % (PROGNAME, kmname, time.asctime()))

    reporter = report.ReportUniqueDates(pargs.use_local)

    las = laspy.file.File(pargs.las_file, mode='r')

    datetimes = find_unique_days(las.gps_time)
    datestrings = [d.strftime('%Y%m%d') for d in datetimes]

    unique_dates = ';'.join(datestrings)
    min_date = np.min(las.gps_time)
    max_date = np.max(las.gps_time)

    reporter.report(
        kmname,
        str(to_datetime(min_date)),
        str(to_datetime(max_date)),
        unique_dates,
        wkt_geom=wkt
    )

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

