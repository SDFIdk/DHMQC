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
Manipulate pointcloud data by either reclassifying points, fixing timestamps
or filling data voids with data from another datasource.
'''
from __future__ import print_function

import sys
import os
import time
import tempfile
import json

import numpy as np
import laspy

from thatsDEM import pointcloud, vector_io, array_geometry
import dhmqc_constants as constants
from utils.osutils import ArgumentParser, run_command

HAYSTACK = os.path.realpath(os.path.join(os.path.dirname(__file__), 'bin', 'haystack'))
PROGNAME = os.path.basename(__file__).replace('.pyc', '.py')
CS_BURN = 0.4
CS_BURN_BUILD = 0.2  # finer granularity - consider shrinking slightly
OLD_TERRAIN = 5  # old terrain class from 2007
SPIKE_CLASS = 1  # to unclass
RECLASS_DEFAULT = 18  # high noise
BUILDING_RECLASS = { # reclassification inside buildings:
    constants.terrain: 19,
    constants.low_veg: 20,
    }

parser = ArgumentParser(
    description='''Perform a range of classification modifications in one go.
                   Do NOT read and write from the same disk!''',
    prog=PROGNAME,
    )
parser.add_argument('las_file', help='input 1km las tile.')
parser.add_argument(
    'outdir',
    help='Resting place of modified input file.',
    )
# The json definition must be a list of tasks - each element must be a
# list of two elements  (name,  definition) where name is one of the valid
# tasks (see below) and definition is a relevant dict for the task (as
# above)
parser.add_argument(
    '-json_tasks',
    help='''json string/file specifying what to be done.
            Must define a list of tasks (see source).
            If not given an unmodified las file is returned.''',
    )
parser.add_argument('-olaz', action='store_true', help='Output as laz - otherwise las.')


def usage():
    '''
    Print script usage instructions
    '''
    parser.print_help()


class BaseRepairMan(object):
    '''
    Base repairer class.

    Stuff that we can do to repair a pointcloud - should be in sync with output from tests
    signature should be path,kmname,extent and additional params as a dict

    This class is not meant to be used directly and should instead be inherited from.
    Abstract methods will raise a NotImplementedError unless they are implemented by
    child classes.

    Arguments
    ---------

    laspath:        Path to las/laz file.
    kmname:         Kvadratnet name of tile.
    extent:         Extent of tile
    params:         Parameters
    '''
    keys = {}

    def __init__(self, las, kmname, extent, params):
        self.las = las
        self.scale = las.header.scale
        self.offset = las.header.offset
        self.kmname = kmname
        self.extent = extent


        self.params = dict(params)
        for key in self.keys:
            totype = self.keys[key]
            if not key in self.params:
                raise ValueError('You need to define ' + key)
            try:
                self.params[key] = totype(self.params[key])
            except Exception, error_msg:
                print(str(error_msg))
                raise ValueError('Key ' + key + ' must be castable to ' + str(totype))

    def repair(self, points):
        '''
        Abstract verions of repair method.
        '''
        error_msg = 'Child classes of BaseRepairMan must implement the repair function'
        raise NotImplementedError(error_msg)


    def reclass_points(self, points, changes, new_class):
        '''
        Reclassifies points in las that matches points in changes.
        '''
        if not isinstance(changes, np.ndarray):
            # try to fix non-compliant input
            changes = np.array(changes)

        x = points['point']['X']*self.scale[0] + self.offset[0]
        y = points['point']['Y']*self.scale[1] + self.offset[1]

        all_coordinates = np.column_stack((x, y)).view('f8,f8').reshape(-1)
        reclass = changes.view('f8,f8').reshape(-1)
        reclass_indices = np.nonzero(np.in1d(all_coordinates, reclass))[0]

        points['point']['raw_classification'][reclass_indices] = new_class
        return points



class FillHoles(BaseRepairMan):
    '''
    Repairer class that fills data voids with data from another source.
    '''
    keys = {'cstr': unicode, 'sql': str, 'path': unicode}

    def __str__(self):
        return 'FillHoles'

    def repair(self, points):
        features = vector_io.get_features(
            self.params['cstr'],
            layersql=self.params['sql'],
            extent=self.extent,
            )

        n_points = sum([f['n_old'] for f in features])
        holes = np.zeros(n_points, dtype=self.las.points.dtype)

        fname = features[0]['dump_name']
        pc = pointcloud.fromBinary(os.path.join(self.params['path'], fname))

        holes['point']['raw_classification'] = 34 # terrain with synthetic bit on
        holes['point']['pt_src_id'] = 0
        holes['point']['gps_time'] = -123456789

        # The flag_byte describes both return_number (bits 0,1,2), number_of_returns (bits 3,4,5)
        # scan direction (bit 6) and edge of flight line (bit 7)
        # Here we want return number, number of returns and scan direction set to 1
        # and edge of flight line set to 0.
        #
        # CAUTION: THIS ASSUMES A LAS FILE OF DATA FORMAT < 6!
        #
        # Until laspy does append we need to do it in this rather cumbersome way
        # circumventing all the otherwise usefull constructs in laspy!
        holes['point']['flag_byte'] = 9 # in binary: 01001001.

        i_prev = 0
        for feat in features:
            geom = feat.GetGeometryRef().Clone()
            arr = array_geometry.ogrpoly2array(geom)

            pc_ = pc.cut_to_polygon(arr)

            I = range(i_prev, i_prev+pc_.size)
            i_prev += pc_.size

            # Usually laspy would do the scaling for us, but since we are
            # manipulating the raw data directly we need to convert
            # coordinates to properly scaled integers
            holes['point']['X'][I] = (pc_.xy[:, 0] - self.offset[0]) / self.scale[0]
            holes['point']['Y'][I] = (pc_.xy[:, 1] - self.offset[1]) / self.scale[1]
            holes['point']['Z'][I] = (pc_.z - self.offset[2]) / self.scale[2]

        return np.append(points, holes)


class BirdsAndWires(BaseRepairMan):
    '''
    Repairer class that reclassifies floating objects, such as
    birds and wires, as high noise.
    '''
    # Must use the original file in same h-system. Will otherwise f*** up...
    keys = {'cstr': unicode, 'sql_exclude': list, 'sql_include': dict, 'exclude_all': bool}

    def __str__(self):
        return 'BirdsAndWires'

    def repair(self, points):
        path = os.path.join(self.params['path'], self.kmname + '_floating.bin')

        if os.path.exists(path) and os.path.getsize(path) <= 0:
            return

        pc = pointcloud.fromBinary(path)
        georef = [self.extent[0], CS_BURN, 0, self.extent[3], 0, -CS_BURN]
        ncols = int((self.extent[2] - self.extent[0]) / CS_BURN)
        nrows = int((self.extent[3] - self.extent[1]) / CS_BURN)

        assert (ncols * CS_BURN + self.extent[0]) == self.extent[2]
        assert (nrows * CS_BURN + self.extent[1]) == self.extent[3]

        if self.params['exclude_all']:  # use sql_include as a whitelist
            mask = np.zeros((nrows, ncols), dtype=np.bool)
        else:
            mask = np.ones((nrows, ncols), dtype=np.bool)
            for sql in self.params['sql_exclude']:
                mask_ = vector_io.burn_vector_layer(
                    self.params['cstr'],
                    georef, (nrows, ncols),
                    layersql=sql
                    )
                mask[mask_] = 0

        class_maps = []
        for c in self.params['sql_include']:  # explicitely included with desired class
            sql = self.params['sql_include'][c]
            mask_ = vector_io.burn_vector_layer(
                self.params['cstr'],
                georef,
                (nrows, ncols),
                layersql=sql
                )
            mask[mask_] = 1
            class_maps.append((mask_, c))

        pc = pc.cut_to_grid_mask(mask, georef)
        rc = np.ones((pc.size,), dtype=np.float64) * RECLASS_DEFAULT

        for M, c in class_maps:
            MM = pc.get_grid_mask(M, georef)
            rc[MM] = c

        return self.reclass_points(points, pc.xy, rc)


class Spikes(BaseRepairMan):
    '''
    Repairer class that reclassifies spikes as noise.
    '''
    keys = {'cstr': unicode, 'sql': str}

    def __str__(self):
        return 'RepairSpikes'

    def repair(self, points):
        features = vector_io.get_features(
            self.params['cstr'],
            layersql=self.params['sql'],
            extent=self.extent,
            )

        spikes = [(f['x'], f['y']) for f in features]
        return self.reclass_points(points, spikes, SPIKE_CLASS)


class CleanBuildings(BaseRepairMan):
    '''
    Repairer class that reclassifies terrain and vegetation points
    inside buildings as custom classes 18 (terrain in building) and
    19 (vegetation in building).
    '''
    keys = {'cstr': unicode, 'sql': str}

    def __str__(self):
        return 'CleanBuildings'

    def repair(self, points):
        georef = [self.extent[0], CS_BURN_BUILD, 0, self.extent[3], 0, -CS_BURN_BUILD]
        ncols = int((self.extent[2] - self.extent[0]) / CS_BURN_BUILD)
        nrows = int((self.extent[3] - self.extent[1]) / CS_BURN_BUILD)

        assert (ncols * CS_BURN_BUILD + self.extent[0]) == self.extent[2]
        assert (nrows * CS_BURN_BUILD + self.extent[1]) == self.extent[3]

        build_mask = vector_io.burn_vector_layer(
            self.params['cstr'],
            georef, (nrows, ncols),
            layersql=self.params['sql'],
            all_touched=False,
            )

        if not build_mask.any():
            return

        pc = pointcloud.fromLaspy(self.las)
        pc = pc.cut_to_class(BUILDING_RECLASS.keys())
        pc = pc.cut_to_grid_mask(build_mask, georef)

        if pc.size <= 0:
            return

        for c in BUILDING_RECLASS:
            rc = BUILDING_RECLASS[c]
            pc_ = pc.cut_to_class(c)
            points = self.reclass_points(points, pc_.xy, rc)

        return points

# The tasks that we can do - the definition may contain more than one of
# each, Allows for including various filtering output in e.g. the
# "birds_and_wires" task
TASKS = {
    'fill_holes': FillHoles,
    'birds_and_wires': BirdsAndWires,
    'spikes': Spikes,
    'clean_buildings': CleanBuildings,
}

def generate_task_list(pargs, las):
    '''
    Create list of tasks to process in main.

    Input:
    ------

    pargs:          Arguments from parser
    las:            Laspy object of input file. Assumed ead-only.
    points:         Writable copy of las.points. Will be modified when running tasks.

    Returns:
    --------

    List of BaseRepairMan tasks to be executed.
    '''

    fargs = {}  # dict for holding reference names
    tasks = []  # a list of the tasks that we wanna do...

    # basic setup stuff
    kmname = constants.get_tilename(pargs.las_file)
    extent = constants.tilename_to_extent(kmname)

    # should probably not be printed from here...
    print('Running %s on block: %s, %s' % (PROGNAME, kmname, time.asctime()))

    if pargs.json_tasks is not None:
        task_def = pargs.json_tasks
        if task_def.endswith('.json'):
            with open(task_def) as task_def_file:
                fargs = json.load(task_def_file)
        else:
            fargs = json.loads(task_def)
        # test the defined json tasks and see if it's one of the valid tasks
        for task in fargs:
            task_name = task[0]
            task_def = task[1]
            if not task_name in TASKS:
                raise ValueError('Name "' + task_name + '" not mapped to any task')
            task_class = TASKS[task_name]
            print('Was told to do ' + task_name + ' - checking params.')
            tasks.append(task_class(las, kmname, extent, task_def))  # append the task

        return tasks


def main(args):
    '''
    Main processing algorithm. Called either stand-alone or from qc_wrap.
    '''
    try:
        pargs = parser.parse_args(args[1:])
    except Exception, error_msg:
        print(str(error_msg))
        return 1

    basename = os.path.splitext(os.path.basename(pargs.las_file))[0]
    ext = '.laz' if pargs.olaz else '.las'

    ilas_path = pargs.las_file
    olas_path = os.path.join(pargs.outdir, basename+ext)
    temp_laz_path = None

    ilas = laspy.file.File(ilas_path, mode='r')
    header = ilas.header.copy()
    if pargs.olaz:
        temp_laz_path = os.path.join(tempfile.gettempdir(), basename+ext)
        olas = laspy.file.File(temp_laz_path, mode='w', header=header)
    else:
        olas = laspy.file.File(olas_path, mode='w', header=header)

    if not os.path.exists(pargs.outdir):
        os.mkdir(pargs.outdir)

    # points needs to be a physical copy of ilas.points
    # since it is altered by the repairer object before
    # writing the contents of points to the output
    # las file, olas.
    points = np.copy(ilas.points)

    tasks = generate_task_list(pargs, ilas)
    for task in tasks:
        points = task.repair(points)

    olas.points = points
    olas.header.global_encoding = 1

    # software_id needs to be exactly 32 chars! Would be nice to have version
    # number or git revision here as well.
    olas.header.software_id = '{:<32}'.format('DHMQC')
    olas.header.system_id = '{:<32}'.format('MODIFICATION') # as per the las 1.1-1.4 spec

    ilas.close()
    olas.close()

    if pargs.olaz:
        cmd = ['laszip-cli', '-i', temp_laz_path, '-o', olas_path]
        run_command(cmd)

    return 0

# to be able to call the script 'stand alone'
if __name__ == '__main__':
    main(sys.argv)
