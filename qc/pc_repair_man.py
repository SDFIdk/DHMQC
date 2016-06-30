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
import sys,os,time
#import some relevant modules...
from thatsDEM import pointcloud, vector_io, array_geometry
from db import report
import numpy as np
import dhmqc_constants as constants
import json
from utils.osutils import ArgumentParser, run_command  #If you want this script to be included in the test-suite use this subclass. Otherwise argparse.ArgumentParser will be the best choice :-)
HAYSTACK=os.path.realpath(os.path.join(os.path.dirname(__file__),"bin","haystack"))
#import haystack_wrapper
#To always get the proper name in usage / help - even when called from a wrapper...
progname=os.path.basename(__file__).replace(".pyc",".py")
#some globals
cs_burn=0.4
cs_burn_build=0.2 #finer granularity - consider shrinking slightly
old_terrain=5 #old terrain class from 2007
spike_class=1  #to unclass
reclass_default=18 #high noise
terrain_in_buildings=19
low_veg_in_buildings=20
med_veg_in_buildings=21
#Argument handling - if module has a parser attributte it will be used to check arguments in wrapper script.
#a simple subclass of argparse,ArgumentParser which raises an exception in stead of using sys.exit if supplied with bad arguments...
parser=ArgumentParser(description="Perform a range of classification modifications in one go. Do NOT read and write from the same disk!",prog=progname)
parser.add_argument("las_file",help="input 1km las tile.")
parser.add_argument("outdir",help="Resting place of modified input file.")
parser.add_argument("-json_tasks",help="json string/file specifying what to be done. Must define a list of tasks (see source).\nIf not given -doall is set to True and default modifications are done.")
parser.add_argument("-doall",action="store_true",help="Repair all tiles, even if there are no reclassifications or fill-ins")
parser.add_argument("-olaz",action="store_true",help="Output as laz - otherwise las.")


#The key that must be defined - and the dependencies if True
HOLE_KEYS={"cstr":unicode,"sql":str,"path":unicode}
BW_KEYS={"cstr":unicode,"sql_exclude":list,"sql_include":dict,"exclude_all":bool}
SPIKE_KEYS={"cstr":unicode,"sql":str}
BUILDING_KEYS={"cstr":unicode,"sql":str}

#The json definition must be a list of tasks - each element must be a list of two elements  (name,  definition) where name is one of the valid tasks (see below) and definition is a relevant dict for the task (as above)

spike_class=1  #to unclass
#reclassification inside buildings:
building_reclass={constants.terrain:19,constants.low_veg:20}

#a usage function will be import by wrapper to print usage for test - otherwise ArgumentParser will handle that...
def usage():
    parser.print_help()
    
#Stuff that we can do to repair a pointcloud - should be in sync with output from tests
#signature should be path,kmname,extent and additional params as a dict
class BaseRepairMan(object):
    keys={}
    def __init__(self,laspath,kmname,extent,params):
        self.laspath=laspath
        self.kmname=kmname
        self.extent=extent
        self.params=dict(params)
        for key in self.keys: 
            totype=self.keys[key]
            if not key in self.params:
                raise ValueError("You need to define "+key)
            try:
                self.params[key]=totype(self.params[key])
            except Exception,e:
                print(str(e))
                raise ValueError("Key "+key+" must be castable to "+str(totype))
    def repair(self):
        return np.empty((0,6),dtype=np.float64)
    
class FillHoles(BaseRepairMan):
    keys=HOLE_KEYS
    def __str__(self):
        return "FillHoles"
    def repair(self):
        features=vector_io.get_features(self.params["cstr"],layersql=self.params["sql"],extent=self.extent)
        xyzcpc=np.empty((0,6),dtype=np.float64)
        pc=None
        print("Holes: %d" %len(features))
        for feat in features:
            geom=feat.GetGeometryRef().Clone()
            arr=array_geometry.ogrpoly2array(geom)
            if pc is None:
                fname=feat["dump_name"]
                pc=pointcloud.fromAny(os.path.join(self.params["path"],fname))
            pc_=pc.cut_to_polygon(arr)
            xyzcpc_=np.column_stack((pc_.xy,pc_.z,np.ones_like(pc_.z)*old_terrain,np.ones_like(pc_.z),np.ones_like(pc_.z)*constants.terrain))
            xyzcpc=np.vstack((xyzcpc,xyzcpc_))
        return xyzcpc

class BirdsAndWires(BaseRepairMan):
    #Must use the original file in same h-system. Will otherwise f*** up...
    keys=BW_KEYS
    def __str__(self):
        return "BirdsAndWires"
    def repair(self):
        path=os.path.join(self.params["path"],self.kmname+"_floating.bin")
        xyzcpc=np.empty((0,6),dtype=np.float64)
       
        if os.path.exists(path) and os.path.getsize(path)>0:
            pc=pointcloud.fromAny(path)
            georef=[self.extent[0],cs_burn,0,self.extent[3],0,-cs_burn]
            ncols=int((self.extent[2]-self.extent[0])/cs_burn)
            nrows=int((self.extent[3]-self.extent[1])/cs_burn)
            assert((ncols*cs_burn+self.extent[0])==self.extent[2])
            assert((nrows*cs_burn+self.extent[1])==self.extent[3])
            if self.params["exclude_all"]: #use sql_include as a whitelist
                 mask=np.zeros((nrows,ncols),dtype=np.bool)
            else:
                mask=np.ones((nrows,ncols),dtype=np.bool)
                for sql in self.params["sql_exclude"]:
                    mask_=vector_io.burn_vector_layer(self.params["cstr"],georef,(nrows,ncols),layersql=sql)
                    mask[mask_]=0
            class_maps=[]    
            for c in self.params["sql_include"]: #explicitely included with desired class
                sql=self.params["sql_include"][c]
                mask_=vector_io.burn_vector_layer(self.params["cstr"],georef,(nrows,ncols),layersql=sql)
                mask[mask_]=1
                class_maps.append((mask_,c))
            pc=pc.cut_to_grid_mask(mask,georef)
            rc=np.ones((pc.size,),dtype=np.float64)*reclass_default
            for M,c in class_maps:
                MM=pc.get_grid_mask(M,georef)
                rc[MM]=c
            return np.column_stack((pc.xy,pc.z,pc.c.astype(np.float64),pc.pid.astype(np.float64),rc))
        return xyzcpc


class Spikes(BaseRepairMan):
    keys=SPIKE_KEYS
    def __str__(self):
        return "RepairSpikes"
    def repair(self):
        features=vector_io.get_features(self.params["cstr"],layersql=self.params["sql"],extent=self.extent)
        data=[]
        for f in features:
            row=(f["x"],f["y"],f["z"],float(f["c"]),f["pid"],float(spike_class))
            data.append(row)
        if len(data)==0:
            return np.empty((0,6),dtype=np.float64)
        data=np.asarray(data,dtype=np.float64)
        return np.atleast_2d(data)
            

class CleanBuildings(BaseRepairMan):
    keys=BUILDING_KEYS
    def __str__(self):
        return "CleanBuildings"
    def repair(self):
        xyzcpc=np.empty((0,6),dtype=np.float64)
        georef=[self.extent[0],cs_burn_build,0,self.extent[3],0,-cs_burn_build]
        ncols=int((self.extent[2]-self.extent[0])/cs_burn_build)
        nrows=int((self.extent[3]-self.extent[1])/cs_burn_build)
        assert((ncols*cs_burn_build+self.extent[0])==self.extent[2])
        assert((nrows*cs_burn_build+self.extent[1])==self.extent[3])
        build_mask=vector_io.burn_vector_layer(self.params["cstr"],georef,(nrows,ncols),layersql=self.params["sql"],all_touched=False)
        if build_mask.any():
            pc=pointcloud.fromAny(self.laspath).cut_to_class(building_reclass.keys()).cut_to_grid_mask(build_mask,georef)
            if pc.size>0:
                for c in building_reclass:
                    rc=building_reclass[c]
                    pc_=pc.cut_to_class(c)
                    xyzcpc_=np.column_stack((pc_.xy,pc_.z,pc_.c.astype(np.float64),pc_.pid.astype(np.float64),np.ones_like(pc_.z)*rc))
                    xyzcpc=np.vstack((xyzcpc,xyzcpc_))
                    
        return xyzcpc

#The tasks that we can do - the definition may contain more than one of each, Allows for including various filterting outpyt in e.g. the "birds_and_wires" task
TASKS={"fill_holes":FillHoles,"birds_and_wires":BirdsAndWires,"spikes":Spikes,"clean_buildings":CleanBuildings}


def main(args):
    try:
        pargs=parser.parse_args(args[1:])
    except Exception,e:
        print(str(e))
        return 1
    kmname=constants.get_tilename(pargs.las_file)
    print("Running %s on block: %s, %s" %(progname,kmname,time.asctime()))
    extent=constants.tilename_to_extent(kmname)
    fargs={} #dict for holding reference names
    tasks=[] # a list of the tasks that we wanna do...
    
    if pargs.json_tasks is not None:
        task_def=pargs.json_tasks
        if task_def.endswith(".json"):
            with open(task_def) as f:
                fargs=json.load(f)
        else:
            fargs=json.loads(task_def)
        #test the defined json tasks and see if it's one of the valid tasks
        for task in fargs:
            task_name=task[0]
            task_def=task[1]
            if not task_name in TASKS:
                raise ValueError("Name '"+task_name+" not mapped to any task")
            task_class=TASKS[task_name]
            print("Was told to do "+task_name+" - checking params.")
            tasks.append(task_class(pargs.las_file,kmname,extent,task_def)) #append the task 
    else:
        print("Parameter file was not specified - just patching with default modifications. Setting doall to True.")
        pargs.doall=True
    if not os.path.exists(pargs.outdir):
        os.mkdir(pargs.outdir)
    xyzcpc_add=np.empty((0,6),dtype=np.float64)
    xyzcpc_reclass=np.empty((0,6),dtype=np.float64)
    #do all tasks - each task either adds points to the reclass array or to the add array. This could be stored in the class as an attr.
    for task in tasks:
        print("Doing "+str(task))
        xyzcpc_=task.repair()
        print("Adding %d pts." %xyzcpc_.shape[0])
        if isinstance(task,FillHoles):
            xyzcpc_add=np.vstack((xyzcpc_add,xyzcpc_))
        else:
            xyzcpc_reclass=np.vstack((xyzcpc_reclass,xyzcpc_))
  
    oname_add=os.path.join(pargs.outdir,kmname+"_add.patch")
    oname_reclass=os.path.join(pargs.outdir,kmname+"_reclass.patch")
    doit=False or pargs.doall
    basename=os.path.splitext(os.path.basename(pargs.las_file))[0]
    ext=".las"
    if pargs.olaz:
        ext=".laz"
    cmd=[HAYSTACK,"-o",os.path.join(pargs.outdir,basename+ext)]
    if xyzcpc_add.shape[0]>0:
        print("Writing "+oname_add+" with %d points" %xyzcpc_add.shape[0])
        xyzcpc_add.tofile(oname_add)
        cmd+=["-a",oname_add]
        doit=True
    if xyzcpc_reclass.shape[0]>0:
        print("Writing "+oname_reclass+" with %d points" %xyzcpc_reclass.shape[0])
        print("New classes: %s" %(str(np.unique(xyzcpc_reclass[:,-1]))))
        xyzcpc_reclass.tofile(oname_reclass)
        cmd+=["-r",oname_reclass]
        doit=True
    if doit:
        path=pargs.las_file
        cmd.append(path)
        print(str(cmd))
        rc,stdout,stderr=run_command(cmd)
        if rc!=0:
            print(stderr)
            raise Exception("Something went wrong, return code: %d" %rc)
        
            

#to be able to call the script 'stand alone'
if __name__=="__main__":
    main(sys.argv)
