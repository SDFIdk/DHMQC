# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Ui_PcPlot.ui'
#
# Created: Wed Jun 04 10:46:29 2014
#      by: PyQt4 UI code generator 4.10
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(957, 397)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label = QtGui.QLabel(Dialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.txt_las_path = QtGui.QLineEdit(Dialog)
        self.txt_las_path.setObjectName(_fromUtf8("txt_las_path"))
        self.horizontalLayout.addWidget(self.txt_las_path)
        self.bt_browse = QtGui.QPushButton(Dialog)
        self.bt_browse.setObjectName(_fromUtf8("bt_browse"))
        self.horizontalLayout.addWidget(self.bt_browse)
        self.formLayout.setLayout(0, QtGui.QFormLayout.FieldRole, self.horizontalLayout)
        self.verticalLayout.addLayout(self.formLayout)
        self.groupBox = QtGui.QGroupBox(Dialog)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.cb_vectorlayers = QtGui.QComboBox(self.groupBox)
        self.cb_vectorlayers.setEditable(False)
        self.cb_vectorlayers.setObjectName(_fromUtf8("cb_vectorlayers"))
        self.horizontalLayout_2.addWidget(self.cb_vectorlayers)
        self.bt_refresh = QtGui.QPushButton(self.groupBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bt_refresh.sizePolicy().hasHeightForWidth())
        self.bt_refresh.setSizePolicy(sizePolicy)
        self.bt_refresh.setObjectName(_fromUtf8("bt_refresh"))
        self.horizontalLayout_2.addWidget(self.bt_refresh)
        self.verticalLayout.addWidget(self.groupBox)
        self.groupBox_2 = QtGui.QGroupBox(Dialog)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox_2)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.bt_plot2d = QtGui.QPushButton(self.groupBox_2)
        self.bt_plot2d.setObjectName(_fromUtf8("bt_plot2d"))
        self.gridLayout.addWidget(self.bt_plot2d, 0, 0, 1, 1)
        self.bt_plot3d = QtGui.QPushButton(self.groupBox_2)
        self.bt_plot3d.setObjectName(_fromUtf8("bt_plot3d"))
        self.gridLayout.addWidget(self.bt_plot3d, 0, 1, 1, 1)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 0, 2, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_2)
        self.txt_log = QtGui.QTextEdit(Dialog)
        self.txt_log.setObjectName(_fromUtf8("txt_log"))
        self.verticalLayout.addWidget(self.txt_log)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Dialog", None))
        self.label.setText(_translate("Dialog", "Path to las tiles:", None))
        self.bt_browse.setText(_translate("Dialog", "Browse", None))
        self.groupBox.setTitle(_translate("Dialog", "Selected polygon  layer", None))
        self.bt_refresh.setText(_translate("Dialog", "Refresh", None))
        self.groupBox_2.setTitle(_translate("Dialog", "Plot", None))
        self.bt_plot2d.setText(_translate("Dialog", "2d plot", None))
        self.bt_plot3d.setText(_translate("Dialog", "3d plot", None))

