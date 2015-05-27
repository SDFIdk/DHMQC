# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Dev\GSTudvikler\newdhmqc\pcplot\Ui_glviewer.ui'
#
# Created: Sun May 17 16:31:14 2015
#      by: PyQt4 UI code generator 4.10.2
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

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("Form"))
        Form.resize(745, 381)
        self.verticalLayout = QtGui.QVBoxLayout(Form)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.rdb_color_by_pid = QtGui.QRadioButton(Form)
        self.rdb_color_by_pid.setObjectName(_fromUtf8("rdb_color_by_pid"))
        self.gridLayout.addWidget(self.rdb_color_by_pid, 0, 2, 1, 1)
        self.rdb_color_by_rn = QtGui.QRadioButton(Form)
        self.rdb_color_by_rn.setObjectName(_fromUtf8("rdb_color_by_rn"))
        self.gridLayout.addWidget(self.rdb_color_by_rn, 0, 1, 1, 1)
        self.bt_reset_view = QtGui.QPushButton(Form)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.bt_reset_view.sizePolicy().hasHeightForWidth())
        self.bt_reset_view.setSizePolicy(sizePolicy)
        self.bt_reset_view.setObjectName(_fromUtf8("bt_reset_view"))
        self.gridLayout.addWidget(self.bt_reset_view, 0, 6, 1, 1)
        self.rdb_color_by_class = QtGui.QRadioButton(Form)
        self.rdb_color_by_class.setChecked(True)
        self.rdb_color_by_class.setObjectName(_fromUtf8("rdb_color_by_class"))
        self.gridLayout.addWidget(self.rdb_color_by_class, 0, 0, 1, 1)
        self.bt_ps_plus = QtGui.QPushButton(Form)
        self.bt_ps_plus.setObjectName(_fromUtf8("bt_ps_plus"))
        self.gridLayout.addWidget(self.bt_ps_plus, 0, 4, 1, 1)
        self.bt_ps_minus = QtGui.QPushButton(Form)
        self.bt_ps_minus.setObjectName(_fromUtf8("bt_ps_minus"))
        self.gridLayout.addWidget(self.bt_ps_minus, 0, 5, 1, 1)
        self.rdb_color_by_z = QtGui.QRadioButton(Form)
        self.rdb_color_by_z.setObjectName(_fromUtf8("rdb_color_by_z"))
        self.gridLayout.addWidget(self.rdb_color_by_z, 0, 3, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Form", "Form", None))
        self.rdb_color_by_pid.setText(_translate("Form", "color by point id", None))
        self.rdb_color_by_rn.setText(_translate("Form", "color by return number", None))
        self.bt_reset_view.setText(_translate("Form", "reset", None))
        self.rdb_color_by_class.setText(_translate("Form", "color by classification", None))
        self.bt_ps_plus.setText(_translate("Form", "point_size++", None))
        self.bt_ps_minus.setText(_translate("Form", "point_size--", None))
        self.rdb_color_by_z.setText(_translate("Form", "color by elevation", None))

