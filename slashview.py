from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from PyQt4.QtOpenGL import *
import traceback
import threading
import sys, os
from pcplot.glviewer import ViewerContainer,ABOUT
from qc.thatsDEM import pointcloud



        

class RedirectOutput(object):
    def __init__(self,win,signal):
        self.win=win
        self.signal=signal
        self.buffer=""
    def write(self,text):
        self.buffer+=text
        if self.buffer[-1]=="\n":
            self.flush()
    def flush(self):
        if len(self.buffer)==0:
            return
        if self.buffer[-1]=="\n":
            self.win.emit(self.signal,self.buffer[:-1])
        else:
            self.win.emit(self.signal,self.buffer)
        self.buffer=""

class TextViewer(QDialog):
    """Class to display text output"""
    def __init__(self,parent):
        QDialog.__init__(self,parent)
        self.setWindowTitle("Log")
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self.txt_field=QTextEdit(self)
        self.txt_field.setCurrentFont(QFont("Courier",9))
        self.txt_field.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self.txt_field.setReadOnly(True)
        self.txt_field.setMinimumSize(600,200)
        #self.setMinimumSize(600,400)
        layout=QVBoxLayout(self)
        layout.addWidget(self.txt_field)
    def log(self,text,color):
        self.txt_field.setTextColor(QColor(color))
        self.txt_field.append(text)
        self.txt_field.ensureCursorVisible()
   


     
        

class LasViewer(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setWindowTitle("LasViewer")
        self.container= ViewerContainer(self)
        self.setCentralWidget(self.container)
        self.actionOpen=QtGui.QAction("Open", self)
        self.actionAbout=QtGui.QAction("About", self)
        self.actionExit=QtGui.QAction("Exit", self)
        self.connect(self.actionOpen,QtCore.SIGNAL('triggered()'),self.onOpenFile)
        self.connect(self.actionAbout,QtCore.SIGNAL('triggered()'),self.onAbout)
        self.connect(self.actionExit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(self.actionOpen)
        fileMenu.addAction(self.actionExit)
        fileMenu.addSeparator()
        fileMenu.addAction(self.actionAbout)
        self.dir="/"
        self.logWindow=TextViewer(self)
        #threading stuff
        self.background_task_signal=QtCore.SIGNAL("__my_backround_task")
        self.log_stdout_signal=QtCore.SIGNAL("__stdout_signal")
        self.log_stderr_signal=QtCore.SIGNAL("__stderr_signal")
        QtCore.QObject.connect(self, self.background_task_signal, self.finishBackgroundTask)
        QtCore.QObject.connect(self, self.log_stdout_signal, self.logStdout)
        QtCore.QObject.connect(self, self.log_stderr_signal, self.logStderr)
        for widget in self.container.color_selection:
            self.connect(widget,QtCore.SIGNAL('clicked()'), self.onChangeColorMode)
        self.finish_method=None
        self.pc=None
        self.err_msg=None
        self.container.setLoadedState(False)
        #redirect textual output
        sys.stdout=RedirectOutput(self,self.log_stdout_signal)
        sys.stderr=RedirectOutput(self,self.log_stderr_signal)
        self.show()
        QMessageBox.information(self,"Movement","Use first and second mouse button as well as 'asdw' to move around.")
    
  
        
    def onAbout(self):
        msg=ABOUT
        QMessageBox.about(self,"About",msg)
    def onOpenFile(self):
        my_file = unicode(QFileDialog.getOpenFileName(self, "Select a vector-data input file",self.dir))
        if len(my_file)>0:
            self.dir=os.path.dirname(my_file)
            self.logWindow.show()
            self.log("Opening "+my_file+"...","orange")
            self.runInBackground(self.loadInBackground,self.finishLoading,(my_file,))
    
    def onChangeColorMode(self):
        if self.pc is not None:
             self.runInBackground(self.bufferInBackground,self.finishLoading,(False,))
    #Stuff for background processing
    def runInBackground(self,run_method,finish_method,args):
        #self.log("thread_id: {0:s}".format(threading.currentThread().name),"blue")
        self.finish_method=finish_method
        self.setEnabled(False)
        thread=threading.Thread(target=run_method,args=args)
        #probably exceptions in the run method should be handled there in order to avoid a freeze...
        thread.start()
    #This is called from an emmitted event - the last execution from the run method...
    def finishBackgroundTask(self):
        #self.log("thread_id: {0:s}".format(threading.currentThread().name),"blue")
        self.setEnabled(True)
        if self.finish_method is not None:
            self.finish_method()
   
    def bufferInBackground(self,reset_position=True):
        try:
            self.container.bufferInBackground(self.pc,reset_position)
        except Exception as e:
            self.pc=None
            self.err_msg=traceback.format_exc()
            self.err_msg+="\n"+str(e)
        self.emit(self.background_task_signal)
            
    def loadInBackground(self,my_file):
        try:
            self.pc=pointcloud.fromAny(my_file,include_return_number=True)
        except Exception as e:
            self.pc=None
            self.err_msg=str(e)
            self.emit(self.background_task_signal)
        else:
            self.err_msg=None
            self.container.viewer.camera_reset()
            self.bufferInBackground()
           
    def finishLoading(self):
        if self.pc is None:
            self.container.setLoadedState(False)
            raise Exception(self.err_msg+"\nDo you have laszip in your PATH?")
        else:
            self.container.setLoadedState(True)
        self.container.viewer.setFocus()
           
    
    def logLater(self,text):
        self.emit(self.log_stdout_signal,text)
    
    def log(self,text,color="blue"):
        self.logWindow.log(text,color)
    @pyqtSlot(str)
    def logStderr(self,text):
        self.logWindow.log(text,"red")
    @pyqtSlot(str)
    def logStdout(self,text):
        self.logWindow.log(text,"blue")
 
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    window = LasViewer()
    sys.exit(app.exec_())


