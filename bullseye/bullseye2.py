#!/usr/bin/python
# -*- coding: utf8 -*-
#
#   bullseye - ccd laser beam profilers (pydc1394 + chaco)
#   Copyright (C) 2012 Robert Jordens <jordens@phys.ethz.ch>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PySide import QtGui, QtCore
import numpy as np
import pyqtgraph as pg


class Bullseye(object):
    def __init__(self, proc):
        self.process = proc
        self.process.initialize()
        self.setup_plots()
        self.update_data()
        self.populate_plots()

    @classmethod
    def run(cls, *args, **kwargs):
        app = pg.mkQApp()
        obj = cls(*args, **kwargs)
        app.exec_()

    def setup_plots(self):
        pg.setConfigOptions(antialias=True)
        win = QtGui.QMainWindow()
        #win = pg.GraphicsWindow()
        win.setWindowTitle("Bullseye")
        win.resize(1000, 600)
        cw = QtGui.QWidget()
        win.setCentralWidget(cw)
        l = QtGui.QGridLayout()
        cw.setLayout(l)
        imv1 = pg.ImageView()
        imv2 = pg.ImageView()
        l.addWidget(imv1, 0, 0)
        l.addWidget(imv2, 1, 0)
        win.show()

    
    def update_data(self):
        pass

    def populate_plots(self):
        pass

    def __del__(self):
        self.close()

    def close(self):
        self.process.stop()
