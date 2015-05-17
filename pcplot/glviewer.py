####################################
### OpenGL LasViewer inspired by Laspy's glviewer #
####################################


from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from PyQt4.QtOpenGL import *
import OpenGL.GL as gl 
import OpenGL.GLU as glu 
from OpenGL.arrays import vbo
import math
import numpy as np
from Ui_glviewer import Ui_Form as Ui_Container


CLS_MAP={1:(0.9,0.9,.9),6:(0.8,0,0),9:(0,0,0.9),2:(0.6,0.5,0),3:(0,0.8,0),4:(0,0.6,0),5:(0.1,0.9,0),17:(0,0.3,0.9),18:(0.1,0.5,0.5)}
COLOR_LIST=((0.9,0,0),(0,0.9,0),(0,0,0.9),(0.7,0.8,0),(0,0.8,0.7))
ABOUT="Las viewer using PyQt4 inspired by laspy's glviewer"

def class_to_color(cls):
    colors=np.ones((cls.shape[0],3),dtype=np.float32)*0.5
    for c in CLS_MAP:
        colors[cls==c]=CLS_MAP[c]
    return colors

def discrete_dimension_to_color(all_vals):
    colors=np.zeros((all_vals.shape[0],3),dtype=np.float32)
    vals=np.unique(all_vals)
    for i,val in enumerate(vals):
        M=(all_vals==val)
        colors[M]=COLOR_LIST[i%len(COLOR_LIST)]
    return colors

def linear_colormap(all_vals,color_low,color_high):
    #TODO
    c1=np.ones((all_vals.shape[0],3),dtype=np.float32)*color_low
    c2=np.ones((all_vals.shape[0],3),dtype=np.float32)*color_high
    m1=np.percentile(all_vals,5)
    m2=np.percentile(all_vals,95)
    dv=((all_vals-m1)/(m2-m1)).reshape((all_vals.shape[0],1))
    dv[dv<0]=0
    dv[dv>1]=1
    colors=c1+c2*dv
    return colors

class VBOProvider(object):
    def __init__(self, x,y,z,colors,center):
        n=x.shape[0]
        i0=0
        vbsize=2000000
        self.vbos=[]
        while i0<n:
            i1=min(n,i0+vbsize)
            data=np.column_stack((x[i0:i1]-center[0],y[i0:i1]-center[1],z[i0:i1]-center[2],colors[i0:i1])).astype(np.float32)
            vbo_= vbo.VBO(data = data,usage = gl.GL_DYNAMIC_DRAW, target = gl.GL_ARRAY_BUFFER)
            self.vbos.append((vbo_,i1-i0))
            i0+=vbsize
    def draw(self):
        for vbo_,n in self.vbos:
            vbo_.bind()
            gl.glVertexPointer(3, gl.GL_FLOAT, 24, vbo_)
            gl.glColorPointer(3, gl.GL_FLOAT, 24, vbo_ + 12)
            gl.glDrawArrays(gl.GL_POINTS, 0, n) 
            vbo_.unbind()
   
class GLViewerWidget(QGLWidget):

    def __init__(self, parent):
        QGLWidget.__init__(self, parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.parent=parent
        self.initial_z=1500
        self.location = np.array([0.0,0.0,self.initial_z])
        self.focus = np.array([0.0,0.0,0.0])
        self.up = np.array([1.0,0.0,0.0])
        self.center=np.array([0.0,0.0,0.0])
        self.data_buffer=None
        self.movement_granularity = 6.0
        self.look_granularity = 16.0
        self.setMinimumSize(500, 500)
        self.oldx = 0
        self.oldy = 0
        self.mouse_speed=0.4
        self.point_size=1

    def increase_point_size(self):
        if self.point_size<5:
            self.point_size+=1
            gl.glPointSize(self.point_size)
            self.update()
            self.setFocus()
            
    def decrease_point_size(self):
        if self.point_size>1:
            self.point_size-=1
            gl.glPointSize(self.point_size)
            self.update()
            self.setFocus()
            
    def set_data(self,x,y,z,colors,reset_position=True):
        self.center[0]=x.mean()
        self.center[1]=y.mean()
        self.center[2]=z.mean()
        if reset_position:
            xmin=x.min()
            ymin=y.min()
            r=max(self.center[0]-xmin,self.center[1]-ymin)
            self.initial_z=r*1.5
            self.location = np.array([0.0,0.0,self.initial_z])
            self.movement_granularity=max(r/500.0*6,1)
        self.data_buffer=VBOProvider(x,y,z,colors,self.center)
        self.update()
        self.setFocus()
     
        
    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glLoadIdentity()
        glu.gluLookAt(self.location[0], self.location[1], self.location[2], 
                      self.focus[0],self.focus[1], self.focus[2] ,
                      self.up[0], self.up[1], self.up[2])
        if self.data_buffer is not None:
            self.draw_points()
            real_pos=self.location+self.center
            self.renderText(10,10,"Position: %.2f,%.2f,%.2f" %(real_pos[0],real_pos[1],real_pos[2]))
            
    def resizeGL(self, w, h):
        ratio = w if h == 0 else float(w)/h
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glViewport(0,0,w,h)
        gl.glLoadIdentity()
        glu.gluPerspective(90,float(ratio),0.001,3000);
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def initializeGL(self):
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        gl.glClearDepth(1.0)

    def draw_points(self):
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_COLOR_ARRAY)
        self.data_buffer.draw()
        gl.glDisableClientState(gl.GL_COLOR_ARRAY)
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        
    def mouseMoveEvent(self, mouseEvent):
        if int(mouseEvent.buttons()) != QtCore.Qt.NoButton :
            # user is dragging
            delta_x = mouseEvent.x() - self.oldx
            delta_y = self.oldy - mouseEvent.y()
            if int(mouseEvent.buttons()) & QtCore.Qt.LeftButton :
                if abs(delta_x)>abs(delta_y):
                    self.camera_yaw(delta_x*0.05)
                else:
                    self.camera_pitch(delta_y*0.05)
                self.update()
            elif int(mouseEvent.buttons()) & QtCore.Qt.RightButton :
                self.camera_roll((delta_x)*0.05)
                self.update()
        self.oldx = mouseEvent.x()
        self.oldy = mouseEvent.y()
    
    def rotate_vector(self, vec_rot, vec_about, theta):
        d = np.sqrt(vec_about.dot(vec_about))
        
        L = np.array((0,vec_about[2], -vec_about[1], 
                    -vec_about[2], 0, vec_about[0],
                    vec_about[1], -vec_about[0], 0))
        L.shape = (3,3)

        
        try:
           R = (np.identity(3) + np.sin(theta)/d*L +
                    (1-np.cos(theta))/(d*d)*(L.dot(L)))
        except:
            print("Error in rotation.")
            return()
        return(vec_rot.dot(R))
    
    
    def camera_reset(self):
        self.location = np.array([0.0,0.0,self.initial_z])
        self.focus = np.array([0.0,0.0,0.0])
        self.up = np.array([1.0,0.0,0.0])
        self.update()
    
    def reset_all(self):
        self.point_size=1
        gl.glPointSize(self.point_size)
        self.camera_reset()
        self.setFocus() #will loose keyboard tracking else :-/



    def camera_move(self,ammount, axis = 1):
      
        if axis == 1:
            pointing = self.focus - self.location
            pnorm = np.sqrt(pointing.dot(pointing))
            pointing /= pnorm
            self.location = self.location + ammount*pointing
            self.focus = self.location + pnorm*pointing
        elif axis == 2:
            pointing = self.focus - self.location
            direction = np.cross(self.up, pointing)
            direction /= np.sqrt(direction.dot(direction))
            self.location = self.location + ammount * direction
            self.focus = self.location + pointing
        elif axis==3:
            pointing = self.focus - self.location
            direction = self.up
            self.location = self.location + ammount * direction
            self.focus = self.location + pointing
            
    def camera_yaw(self, theta):
        pointing = self.focus - self.location
        newpointing = self.rotate_vector(pointing, self.up, theta)
        self.focus = newpointing + self.location

    def camera_roll(self, theta):
        self.up = self.rotate_vector(self.up, self.focus-self.location, theta)

    def camera_pitch(self,theta):
        pointing = self.focus - self.location
        axis = np.cross(self.up, pointing)
        newpointing = self.rotate_vector(pointing, axis, theta)
        self.focus = newpointing + self.location
        self.up = np.cross(newpointing, axis)
        self.up /= np.sqrt(self.up.dot(self.up))
    
    def wheelEvent(self,event):
        if self.data_buffer is not None:
            self.camera_move(event.delta()*self.movement_granularity*0.04)
            real_pos=self.location+self.center
            #self.parent.statusBar().showMessage("Position: %.2f,%.2f,%.2f" %(real_pos[0],real_pos[1],real_pos[2]))
            self.update()
    
    #for this to work - we seemingly need to give focus to this widget from time to time...
    def keyPressEvent(self,event):
        if self.data_buffer is not None:
            if event.key() == QtCore.Qt.Key_A:
                self.camera_move(self.movement_granularity,2)
                self.update()
            elif event.key() == QtCore.Qt.Key_D:
                self.camera_move(-self.movement_granularity,2)
                self.update()
            elif event.key() == QtCore.Qt.Key_W:
                self.camera_move(self.movement_granularity,3)
                self.update()
            elif event.key() == QtCore.Qt.Key_S:
                self.camera_move(-self.movement_granularity,3)
                self.update()
            event.accept()
        else:
            event.ignore()
       
  




class ViewerContainer(QtGui.QWidget,Ui_Container):
    def __init__(self,parent):
        QtGui.QMainWindow.__init__(self,parent)
        self.setupUi(self)
        self.viewer= GLViewerWidget(self)
        self.viewer.setSizePolicy(QSizePolicy.Expanding , QSizePolicy.Expanding )
        self.layout().addWidget(self.viewer)
        #handy pointers
        self.color_selection=[self.rdb_color_by_class,self.rdb_color_by_rn,self.rdb_color_by_pid,self.rdb_color_by_z]
        self.controls=[self.bt_ps_plus,self.bt_ps_minus,self.bt_reset_view]
        #handy pointers
        self.color_selection=[self.rdb_color_by_class,self.rdb_color_by_rn,self.rdb_color_by_pid,self.rdb_color_by_z]
        self.controls=[self.bt_ps_plus,self.bt_ps_minus,self.bt_reset_view]
        self.setLoadedState(False)
    def setLoadedState(self, is_loaded):
        for widget in self.controls:
            widget.setEnabled(is_loaded)
    def getColorMode(self):
        mode="default"
        dim="c"
        if self.rdb_color_by_class.isChecked():
            dim="c"
        elif self.rdb_color_by_rn.isChecked():
            dim="rn"
        elif self.rdb_color_by_pid.isChecked():
            dim="pid"
        elif self.rdb_color_by_z.isChecked():
            dim="z"
        return mode,dim
    @pyqtSignature('') #prevents actions being handled twice
    def on_bt_reset_view_clicked(self):
        self.viewer.reset_all()
    @pyqtSignature('') #prevents actions being handled twice
    def on_bt_ps_plus_clicked(self):
        self.viewer.increase_point_size()
    @pyqtSignature('') #prevents actions being handled twice
    def on_bt_ps_minus_clicked(self):
        self.viewer.decrease_point_size()
    def bufferInBackground(self,pc,reset_position=True):
        mode,dim=self.getColorMode()
        if dim=="c":
            colors=class_to_color(pc.c)
        elif dim=="pid" or dim=="rn":
            colors=discrete_dimension_to_color(pc.__dict__[dim])
        elif dim=="z":
            colors=linear_colormap(pc.z,(0.1,0.1,0.1),(0.9,0.9,0.9))
        self.viewer.set_data(pc.xy[:,0],pc.xy[:,1],pc.z,colors,reset_position)

class GLDialog(QtGui.QDialog):
	def __init__(self,parent,pc):
		QtGui.QMainWindow.__init__(self,parent)
		self.setWindowTitle("OpenGL-plot")
		self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
		self.container=ViewerContainer(self)
		layout=QVBoxLayout(self)
		layout.addWidget(self.container)
		#TODO - add this to background tasks...
		self.pc=pc
		self.container.bufferInBackground(self.pc)
		self.container.setLoadedState(True)
		for widget in self.container.color_selection:
			self.connect(widget,QtCore.SIGNAL('clicked()'), self.onChangeColorMode)
		self.setAttribute(Qt.WA_DeleteOnClose)
	def onChangeColorMode(self):
		self.setEnabled(False)
		self.container.bufferInBackground(self.pc,reset_position=False)
		self.setEnabled(True)
		self.container.viewer.setFocus()
	def closeEvent(self,event):
		self.accept()
	