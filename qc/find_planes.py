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

from __future__ import absolute_import
from __future__ import print_function
from math import degrees,radians,acos,sqrt,cos,sin,atan,tan
import math
from qc.thatsDEM import array_geometry
import numpy as np

DEBUG=False

#ANGLES
MIN_AZIMUTH=18  #max 85 deg slope -> min slope of roof 15
MAX_AZIMUTH=60 #max slope of roof
R1=tan(radians(MIN_AZIMUTH))  #planar radius to start from
R2=tan(radians(MAX_AZIMUTH)) #planar radius to stop at


def plot3d(xy,z1,z2=None,z3=None):
    fig = plt.figure()
    ax = Axes3D(fig)
    ax.scatter(xy[:,0], xy[:,1], z1,s=1.7)
    if z2 is not None:
        ax.scatter(xy[:,0], xy[:,1], z2,s=3.0,color="red")
    if z3 is not None:
        ax.scatter(xy[:,0], xy[:,1], z3,s=3.0,color="green")
    plt.show()


def plot_intersections(a_poly,intersections,line_x,line_y):
    plt.figure()
    plt.axis("equal")
    plt.plot(a_poly[:,0],a_poly[:,1],label="Polygon")
    plt.scatter(intersections[:,0],intersections[:,1],label="Intersections",color="red")
    plt.plot(line_x,line_y,label="Found 'roof ridge'")
    plt.legend()
    plt.show()


def find_planar_pairs(planes):
    if len(planes)<2:
        return None,None

    print(("Finding pairs in %d planes" %len(planes)))
    best_score=1000
    best_pop=0.0000001
    pair=None
    eq=None
    z=None
    for i in range(len(planes)):
        p1=planes[i]
        for j in range(i+1,len(planes)):
            p2=planes[j]
            g_score=((p1[0]+p2[0])**2+(p1[1]+p2[1])**2)+2.0/(p1[-1]+p2[-1]) #bonus for being close, bonus for being steep
            pop=(p1[-2]+p2[-2])
            score=g_score/pop
            if score<best_score or ((best_score/score)>0.85 and pop/best_pop>1.5):
                pair=(i,j)
                best_score=score
                best_pop=pop

    if pair is not None:
        p1=planes[pair[0]]
        p2=planes[pair[1]]
        eq=(p1[0]-p2[0],p1[1]-p2[1],p2[2]-p1[2])  #ax+by=c

    return pair,eq

#important here to have a relatively large bin size.... 0.2m seems ok.
def find_horisontal_planes(z,look_lim=0.2, bin_size=0.2):
    z1=z.min()
    z2=z.max()
    n=max(int(np.round(z2-z1)/bin_size),1)
    h,bins=np.histogram(z,n)
    h=h.astype(np.float64)/z.size

    #TODO: real clustering
    I=np.where(h>=look_lim)[0]  #the bins that are above fraction look_lim
    if I.size==0:
        return None,None
    bin_centers=bins[:-1]+np.diff(bins)

    return bin_centers[I],np.sum(h[I])

def search(v1,v2,r1,r2,xy,z,look_lim=0.1,bin_size=0.2,steps=15):
    assert(r2>r1)
    V=np.linspace(v1,v2,steps)
    R=np.linspace(r1,r2,steps)
    h_max=-1
    found=[]
    found_max=None
    #for now will only one candidate for each pair of a,b
    for v in V:
        for r in R:
            found_here=[]
            a=r*cos(v) #x - might be speedier to precalc??
            b=r*sin(v)  #y
            alpha=degrees(atan(r))  #the angle relative to vertical
            nn=sqrt(r**2+1)
            c=(z-a*xy[:,0]-b*xy[:,1])/nn #normalise to get real projection onto axis...
            zs,ns=array_geometry.moving_bins(c,bin_size*0.5)
            i=np.argmax(ns)   #the most
            f=ns[i]/(float(zs.size))

            if f>look_lim: #and h[i]>3*h.mean(): #this one fucks it up...
                c_m=zs[i]*nn
                here=[v,r,c_m,f,alpha]
                if f>h_max:
                    found_max=here
                    h_max=f
                found.append(here)

    return found_max,found


#A bit of parameter magic going on here,,,
#TODO: make the parameters more visible
def cluster(pc,steps1=15,steps2=20): #number of steps affect running time and precsion of output...
    xy=pc.xy
    z=pc.z
    h_planes,h_frac=find_horisontal_planes(z)
    if h_planes is not None and h_frac>0.75:
        print("Seemingly a house with mostly flat roof at:")
        for z_h in h_planes:
            print(("z=%.2f m" %z_h))
        return []

    fmax,found=search(0,2*math.pi,R1,R2,xy,z,0.2,bin_size=0.22,steps=steps1)
    vrad=2*math.pi/steps1*0.85
    rrad=0.85*(R2-R1)/steps1
    vstep2=vrad/steps2
    rstep2=rrad/steps2
    print(("Initial search resulted in %d planes." %len(found)))
    final_candidates={}
    if len(found)>0:
        for plane in found:
            if DEBUG:
                print(("'Raw' candidate:\n%s" %(plane)))
            v,r=plane[0],plane[1]
            fmax,found2=search(v-vrad,v+vrad,r-rrad,r+rrad,xy,z,0.1,0.1,steps=steps2) #slightly finer search
            #using only fmax, we wont find parallel planes
            if fmax is None:
                continue
            if DEBUG:
                print(("After a closer look we get:\n%s" %(fmax)))
            if fmax[3]>0.12:
                store=True
                for key in final_candidates:
                    p=final_candidates[key]
                    frac=p[3]
                    if frac>fmax[3] and abs(key[0]-fmax[0])<vstep2 and abs(key[1]-fmax[1])<rstep2:
                        store=False
                if store:
                    final_candidates[(fmax[0],fmax[1])]=fmax

        if DEBUG:
            print(("Number of 'final candidates': %d" %len(final_candidates)))
            for key in final_candidates:
                f=final_candidates[key]
                print(("Plotting:\n%s" %(f)))
                a=f[1]*cos(f[0])
                b=f[1]*sin(f[0])
                z1=a*xy[:,0]+b*xy[:,1]+f[2]
                plot3d(xy,z,z1)

    toab=[(f[1]*cos(f[0]),f[1]*sin(f[0]),f[2],f[3],f[4]) for f in final_candidates.values()]
    return toab
