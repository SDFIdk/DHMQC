#####################
## Demo script which loads, grids and shows a pointcloud
######################
import sys
import pointcloud
import matplotlib
matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt
pc=pointcloud.fromLAS(sys.argv[1])
pc.triangulate()
g=pc.get_grid(800,800,crop=10)
bbox=g.get_bounds()
im=plt.imshow(g.grid,extent=(bbox[0],bbox[2],bbox[3],bbox[1]))
plt.colorbar(im)
plt.show()