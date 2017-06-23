# -*- coding: utf8 -*-
#
#   bullseye - ccd laser beam profilers (pydc + chaco)
#   Copyright (C) 2012 Robert Jordens <robert@joerdens.org>
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

from traits.api import (Float, Int, Str, Range, Instance, on_trait_change, Any)

import cv

import logging
import numpy as np

from .capture import BaseCapture


class OpenCVCapture(BaseCapture):
    cam = Any # Instance(cv.Capture)

    pixelsize = Float(3.75)
    maxval = Int((1 << 8) - 1)

    def __init__(self, index=0, **k):
        self.cam = cv.CaptureFromCAM(index)
        super(OpenCVCapture, self).__init__(**k)

    def setup(self):
        self.width = int(cv.GetCaptureProperty(
            self.cam, cv.CV_CAP_PROP_FRAME_WIDTH))
        self.height = int(cv.GetCaptureProperty(
            self.cam, cv.CV_CAP_PROP_FRAME_HEIGHT))
        #self.cam.mode = self.mode
        self.max_framerate = 10
        self.add_trait("framerate", Range(1, 10, 1))
        self.add_trait("shutter", Range(-10, 10, 0))
        self.add_trait("gain", Range(0, 1, .5))
        #cv.SetCaptureProperty(self.cam, cv.CV_CAP_PROP_GAIN, val)

    def start(self):
        pass

    def stop(self):
        pass

    @on_trait_change("gain")
    def _do_gain(self, val):
        cv.SetCaptureProperty(self.cam, cv.CV_CAP_PROP_GAIN, val)

    @on_trait_change("shutter")
    def _do_shutter(self, val):
        cv.SetCaptureProperty(self.cam, cv.CV_CAP_PROP_EXPOSURE, val)

    @on_trait_change("framerate")
    def _do_framerate(self, val):
        cv.SetCaptureProperty(self.cam, cv.CV_CAP_PROP_FPS, val)

    depth2dtype = {
        cv.IPL_DEPTH_8U: 'uint8',
        cv.IPL_DEPTH_8S: 'int8',
        cv.IPL_DEPTH_16U: 'uint16',
        cv.IPL_DEPTH_16S: 'int16',
        cv.IPL_DEPTH_32S: 'int32',
        cv.IPL_DEPTH_32F: 'float32',
        cv.IPL_DEPTH_64F: 'float64',
    }

    def dequeue(self):
        # flush
        cv.GrabFrame(self.cam)
        im = cv.RetrieveFrame(self.cam)
        #cv.Flip(im, None, 1)
        img = cv.CreateImage(cv.GetSize(im), 8, 1)
        cv.CvtColor(im, img, cv.CV_BGR2GRAY)
        im = img
        a = np.fromstring(im.tostring(),
                dtype=self.depth2dtype[im.depth],
                count=im.width*im.height*im.nChannels)
        a.shape = (im.height, im.width, im.nChannels)
        return a[:, :, 0]

    def enqueue(self, im):
        pass

    def flush(self):
        pass
