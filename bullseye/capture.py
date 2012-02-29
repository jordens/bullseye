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
        ListFloat, Instance, Trait, Array, on_trait_change)

import numpy as np
from collections import deque
import logging, time


class BaseCapture(HasTraits):
    pixelsize = Float(1.)
    width = Int(640)
    height = Int(480)
    maxval = Int((1<<8)-1)

    min_shutter = 1.
    max_shutter = 1.
    shutter = Range(1.)
    auto_shutter = Bool(False)
    gain = Range(1.)
    framerate = Range(1)
    max_framerate = Int(1)

    roi = ListFloat(minlen=4, maxlen=4)
    
    dark = Bool(False)
    darkim = Trait(None, None, Array)
    average = Range(1, 20, 1)
    average_deque = Instance(deque, args=([], 20))

    im = Array
    
    save_format = Str

    def __init__(self, **k):
        super(BaseCapture, self).__init__(**k)
        self.setup()
        px = self.pixelsize
        self.roi = [-self.width/px/2, -self.height/px/2,
                self.width, self.height]

    def setup(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    @on_trait_change("shutter, gain")
    def _unset_dark(self):
        self.dark = False

    @on_trait_change("dark")
    def _do_dark(self):
        self.darkim = None # invalidate

    @on_trait_change("roi")
    def update_bounds(self, roi):
        l, b, w, h = roi
        px = self.pixelsize
        l = int(min(self.width, max(0, l/px+self.width/2)))
        b = int(min(self.height, max(0, b/px+self.height/2)))
        w = int(min(self.width-l, max(8, w/px)))
        h = int(min(self.height-b, max(8, h/px)))
        self.bounds = [l, b, w, h]

    def dequeue(self):
        raise NotImplementedError

    def enqueue(self, im):
        pass

    def flush(self):
        pass

    def auto(self, im, percentile=99.9, maxiter=10,
            minval=.25, maxval=.75, adjustment_factor=.5):
        p = np.percentile(im, percentile)/float(self.maxval)
        if not ((p < minval and self.shutter < self.max_shutter) or
                (p > maxval and self.shutter > self.min_shutter)):
            return im # early return before setting framerate
        fr, self.framerate = self.framerate, self.max_framerate
        for i in range(maxiter):
            self.enqueue(im)
            self.flush()
            im = self.dequeue()
            p = np.percentile(im, percentile)/float(self.maxval)
            s = "="
            if p > maxval and self.shutter > self.min_shutter:
                self.shutter = max(self.min_shutter,
                        self.shutter*adjustment_factor)
                s = "-"
            elif p < minval and self.shutter < self.max_shutter:
                self.shutter = min(self.max_shutter,
                        self.shutter/adjustment_factor)
                s = "+"
            logging.debug("1%%>%g, t%s: %g", p, s, self.shutter)
            if s == "=":
                break
            else:
                # ensure all frames with old settings are gone
                self.enqueue(im)
                im = self.dequeue()
        # revert framerate
        self.framerate = fr
        return im

    def capture(self):
        im = self.dequeue()
        if self.auto_shutter:
            im = self.auto(im)
        if self.save_format:
            name = time.strftime(self.save_format)
            np.savez_compressed(name, im)
            logging.debug("saved as %s", name)
        im_ = np.array(im, dtype=np.int, copy=True)
        self.enqueue(im)
        im = im_
        if self.dark:
            if self.darkim is None:
                self.darkim = im
                return None
            else:
                im -= self.darkim
        if self.average == 1:
            self.average_deque.clear()
            self.average_deque.append(im)
            self.im = im
        else:
            if len(self.average_deque) == 1:
                self.im = self.im.copy() # break ref
            while len(self.average_deque) >= self.average:
                self.im -= self.average_deque.popleft()
            self.average_deque.append(im)
            self.im += im
            im = self.im/len(self.average_deque)
        l, b, w, h = self.bounds
        im = im[b:b+h, l:l+w]
        return im


class DummyCapture(BaseCapture):
    def dequeue(self):
        px = self.pixelsize
        x, y = 20., 30.
        a, c = 50/4., 40/4.
        m = .7
        t = np.deg2rad(15.)
        j, i = np.ogrid[:self.height, :self.width]
        i, j = (i-self.width/2)*px-x, (j-self.height/2)*px-y
        i, j = np.cos(t)*i+np.sin(t)*j, -np.sin(t)*i+np.cos(t)*j
        im = self.maxval*m*np.exp(-((i/a)**2+(j/c)**2)/2)
        im *= 1+np.random.randn(*im.shape)*.1
        #im += np.random.randn(im.shape)*30
        return (im+.5).astype(np.uint8)



