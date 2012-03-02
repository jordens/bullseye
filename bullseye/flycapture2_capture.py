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

from traits.api import (Float, Int, Str, Range, Instance, on_trait_change)

import flycapture2 as fc2

import numpy as np
import logging

from .capture import BaseCapture


class Fc2Capture(BaseCapture):
    ctx = Instance(fc2.Context)

    pixelsize = Float(3.75)
    maxval = Int((1 << 8) - 1)

    def __init__(self, index=0, **k):
        self.ctx = fc2.Context()
        self.ctx.connect(*self.ctx.get_camera_from_index(index))
        super(Fc2Capture, self).__init__(**k)

    def setup(self):
        for prop in fc2.AUTO_EXPOSURE, fc2.BRIGHTNESS:
            self._set_feature(prop, on_off=False)
        for prop in fc2.FRAME_RATE, fc2.SHUTTER, fc2.GAIN:
            self._set_feature(prop, auto_manual_mode=False, on_off=True,
                    abs_control=True)
        self.ctx.set_video_mode_and_frame_rate(fc2.VIDEOMODE_1280x960Y8, 
                fc2.FRAMERATE_7_5)
        self.width = 1280
        self.height = 960
        self.min_shutter = 1e-5
        self.max_shutter = .1
        self.add_trait("shutter", Range(
            self.min_shutter, self.max_shutter,
            self._get_feature(fc2.SHUTTER)/1000.))
        self.max_framerate = 10
        self.add_trait("framerate", Range(
            1, self.max_framerate,
            int(self._get_feature(fc2.FRAME_RATE))))
        self.add_trait("gain", Range(
            0., 24.,
            self._get_feature(fc2.GAIN)))

    def _get_feature(self, prop):
        v = self.ctx.get_property(prop)
        return v["abs_value"]

    def _set_feature(self, prop, **kw):
        v = self.ctx.get_property(prop)
        v.update(kw)
        self.ctx.set_property(**v)

    @on_trait_change("framerate")
    def _do_framerate(self, val):
        self._set_feature(fc2.FRAME_RATE, abs_value=val)

    @on_trait_change("shutter")
    def _do_shutter(self, val):
        self._set_feature(fc2.SHUTTER, abs_value=val*1000) # milliseconds

    @on_trait_change("gain")
    def _do_gain(self, val):
        self._set_feature(fc2.GAIN, abs_value=val)

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

    def enqueue(self, im):
        pass # image will be garbage collected
