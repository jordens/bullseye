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

from traits.api import (HasTraits, Float, Int, Str, Range, Bool,
        Instance, on_trait_change)

import flycapture2 as fc2

import numpy as np
import logging

from .capture import BaseCapture


class Fc2Capture(BaseCapture):
    ctx = Instance(fc2.Context)

    pixelsize = Float(3.75)
    maxval = Int((1<<8)-1)
    mode_name = Str("1280x960Y8")

    def __init__(self, index=0, **k):
        self.ctx = fc2.Context()
        self.ctx.connect(*self.ctx.get_camera_from_index(index))
        super(Fc2Capture, self).__init__(**k)

    def start(self):
        try:
            self.ctx.start_capture()
        except fc2.ApiError:
            logging.debug("camera capture already running")

    def stop(self):
        self.ctx.stop_capture()

    def dequeue(self):
        im = fc2.Image()
        self.ctx.retrieve_buffer(im)
        return np.array(im)[:, :, 0]


