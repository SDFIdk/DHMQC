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
#
'''
Find planes - works for 'simple houses' etc...
Useful for finding house edges (where points fall of a plane) and roof 'ridges', where planes intersect...

Houses with parallel roof patches at different heights are problematic - would be better split out into more input polygons...
# work in progress...
'''
from __future__ import print_function

import sys
import os
import time
from math import degrees, acos

import numpy as np

from qc.thatsDEM import pointcloud, vector_io, array_geometry
from qc.db import report
from . import dhmqc_constants as constants
from qc.utils.osutils import ArgumentParser
from qc.find_planes import plot3d, plot_intersections, find_planar_pairs, cluster

DEBUG = "-debug" in sys.argv
# z-interval to restrict the pointcloud to.
Z_MIN = constants.z_min_terrain
Z_MAX = constants.z_max_terrain + 30

# hmm try to only use building classifications here - should be less noisy!
cut_to = [constants.building, constants.surface]


progname = os.path.basename(__file__).replace(".pyc", ".py")

parser = ArgumentParser(
    description="Check displacement of roofridges relative to input polygons",
    prog=progname,
    )

parser.add_argument(
    "-use_all",
    action="store_true",
    help="Check all buildings. Else only check those with 4 corners.",
    )

db_group = parser.add_mutually_exclusive_group()
db_group.add_argument(
    "-use_local",
    action="store_true",
    help="Force use of local database for reporting.",
    )
db_group.add_argument(
    "-schema",
    help="Specify schema for PostGis db.",
    )

parser.add_argument(
    "-class",
    dest="cut_class",
    type=int,
    default=cut_to,
    help="Inspect points of this class - defaults to 'surface' and 'building'",
    )
parser.add_argument(
    "-sloppy",
    action="store_true",
    help="Use all buildings - no geometry restrictions (at all).",
    )
parser.add_argument(
    "-search_factor",
    type=float,
    default=1,
    help="Increase/decrease search factor - may result in larger computational time.",
    )
parser.add_argument(
    "-debug",
    action="store_true",
    help="Increase verbosity...",
    )

group = parser.add_mutually_exclusive_group()
group.add_argument(
    "-layername",
    help="Specify layername (e.g. for reference data in a database)",
    )
group.add_argument(
    "-layersql",
    help="Specify sql-statement for layer selection (e.g. for reference data in a database)",
    type=str,
    )

parser.add_argument(
    "las_file",
    help="input 1km las tile.",
    )
parser.add_argument(
    "build_polys",
    help="input reference building polygons (path or connection string).",
    )


def usage():
    parser.print_help()


# TODO: modularise common code in roof_ridge scripts...
def get_intersections(poly, line):
    # hmmm - not many vertices, probably fast enough to run a python loop
    # TODO: test that all vertices are corners...
    intersections = []
    distances = []
    rotations = []
    a_line = np.array(line[:2])
    n_line = np.sqrt((a_line**2).sum())
    for i in xrange(poly.shape[0] - 1):  # polygon is closed...
        v = poly[i + 1] - poly[i]  # that gives us a,b for that line
        n_v = np.sqrt((v**2).sum())
        cosv = np.dot(v, a_line) / (n_v * n_line)
        try:
            a = degrees(acos(cosv))
        except Exception as e:
            print("Math exception: %s" % str(e))
            continue
        #print("Angle between normal and input line is: %.4f" %a)
        if abs(a) > 20 and abs(a - 180) > 20:
            continue
        else:
            n2 = np.array((-v[1], v[0]))  # normal to 'vertex' line
            c = np.dot(poly[i], n2)
            A = np.vstack((n2, a_line))
            try:
                xy = np.linalg.solve(A, (c, line[2]))
            except Exception as e:
                print("Exception in linalg solver: %s" % (str(e)))
                continue
            xy_v = xy - poly[i]
            # check that we actually get something on the line...
            n_xy_v = np.sqrt((xy_v**2).sum())
            cosv = np.dot(v, xy_v) / (n_v * n_xy_v)
            if abs(cosv - 1) < 0.01 and n_xy_v / n_v < 1.0:
                center = poly[i] + v * 0.5
                d = np.sqrt(((center - xy)**2).sum())
                cosv = np.dot(n2, a_line) / (n_v * n_line)
                try:
                    rot = degrees(acos(cosv)) - 90.0
                except Exception as e:
                    print("Exception finding rotation: %s, numeric instabilty..." % (str(e)))
                    continue
                print("Distance from intersection to line center: %.4f m" % d)
                print("Rotation:                                  %.4f dg" % rot)
                intersections.append(xy.tolist())
                distances.append(d)
                rotations.append(rot)
    return np.asarray(intersections), distances, rotations


# Now works for 'simple' houses...
def main(args):
    pargs = parser.parse_args(args[1:])
    lasname = pargs.las_file
    polyname = pargs.build_polys
    kmname = constants.get_tilename(lasname)
    print("Running %s on block: %s, %s" % (os.path.basename(args[0]), kmname, time.asctime()))
    use_local = pargs.use_local
    if pargs.schema is not None:
        report.set_schema(pargs.schema)
    reporter = report.ReportRoofridgeCheck(use_local)
    cut_class = pargs.cut_class
    print("Using class(es): %s" % (cut_class))
    # default step values for search...
    steps1 = 32
    steps2 = 14
    search_factor = pargs.search_factor
    if search_factor != 1:
        # can turn search steps up or down
        steps1 = int(search_factor * steps1)
        steps2 = int(search_factor * steps2)
        print("Incresing search factor by: %.2f" % search_factor)
        print("Running time will increase exponentionally with search factor...")
    pc = pointcloud.fromAny(lasname).cut_to_class(cut_class).cut_to_z_interval(Z_MIN, Z_MAX)
    try:
        extent = np.asarray(constants.tilename_to_extent(kmname))
    except Exception:
        print("Could not get extent from tilename.")
        extent = None
    polys = vector_io.get_geometries(polyname, pargs.layername, pargs.layersql, extent)
    fn = 0
    sl = "+" * 60
    is_sloppy = pargs.sloppy
    use_all = pargs.use_all
    for poly in polys:
        print(sl)
        fn += 1
        print("Checking feature number %d" % fn)
        a_poly = array_geometry.ogrgeom2array(poly)
        # secret argument to use all buildings...
        if (len(a_poly) > 1 or a_poly[0].shape[0] != 5) and (not use_all) and (not is_sloppy):
            print("Only houses with 4 corners accepted... continuing...")
            continue
        pcp = pc.cut_to_polygon(a_poly)
        # hmmm, these consts should perhaps be made more visible...
        if (pcp.get_size() < 500 and (not is_sloppy)) or (pcp.get_size() < 10):
            print("Few points in polygon...")
            continue
        # Go to a more numerically stable coord system - from now on only consider outer ring...
        a_poly = a_poly[0]
        xy_t = a_poly.mean(axis=0)
        a_poly -= xy_t
        pcp.xy -= xy_t
        pcp.triangulate()
        geom = pcp.get_triangle_geometry()
        m = geom[:, 1].mean()
        sd = geom[:, 1].std()
        if (m > 1.5 or 0.5 * sd > m) and (not is_sloppy):
            print("Feature %d, bad geometry...." % fn)
            print(m, sd)
            continue
        planes = cluster(pcp, steps1, steps2)
        if len(planes) < 2:
            print("Feature %d, didn't find enough planes..." % fn)
        pair, equation = find_planar_pairs(planes)
        if pair is not None:
            p1 = planes[pair[0]]
            p2 = planes[pair[1]]
            z1 = p1[0] * pcp.xy[:, 0] + p1[1] * pcp.xy[:, 1] + p1[2]
            z2 = p2[0] * pcp.xy[:, 0] + p2[1] * pcp.xy[:, 1] + p2[2]
            print("%s" % ("*" * 60))
            print("Statistics for feature %d" % fn)
            if DEBUG:
                plot3d(pcp.xy, pcp.z, z1, z2)
            intersections, distances, rotations = get_intersections(a_poly, equation)
            if intersections.shape[0] == 2:
                line_x = intersections[:, 0]
                line_y = intersections[:, 1]
                z_vals = p1[0] * intersections[:, 0] + p1[1] * intersections[:, 1] + p1[2]
                if abs(z_vals[0] - z_vals[1]) > 0.01:
                    print("Numeric instabilty for z-calculation...")
                z_val = float(np.mean(z_vals))
                print("Z for intersection is %.2f m" % z_val)
                if abs(equation[1]) > 1e-3:
                    a = -equation[0] / equation[1]
                    b = equation[2] / equation[1]
                    line_y = a * line_x + b
                elif abs(equation[0]) > 1e-3:
                    a = -equation[1] / equation[0]
                    b = equation[2] / equation[0]
                    line_x = a * line_y + b
                if DEBUG:
                    plot_intersections(a_poly, intersections, line_x, line_y)
                # transform back to real coords
                line_x += xy_t[0]
                line_y += xy_t[1]
                wkt = "LINESTRING(%.3f %.3f %.3f, %.3f %.3f %.3f)" % (
                    line_x[0], line_y[0], z_val, line_x[1], line_y[1], z_val)
                print("WKT: %s" % wkt)
                reporter.report(kmname, rotations[0], distances[0], distances[1], wkt_geom=wkt)
            else:
                print("Hmmm - something wrong, didn't get exactly two intersections...")


if __name__ == "__main__":
    main(sys.argv)
