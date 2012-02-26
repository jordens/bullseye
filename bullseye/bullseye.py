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

from traits.trait_base import ETSConfig
ETSConfig.toolkit = "qt4"
# fix window color on unity
if ETSConfig.toolkit == "wx":
    from traitsui.wx import constants
    constants.WindowColor = constants.wx.NullColor

from traits.api import (HasTraits, Range, Int, Float, Enum, Bool,
        Unicode, Str, ListFloat, ListInt, Instance, Delegate, Trait,
        Property, on_trait_change, TraitError, Array)

from traitsui.api import (View, Item, UItem,
        HGroup, VGroup, DefaultOverride)

from chaco.api import (Plot, ArrayPlotData, color_map_name_dict,
        GridPlotContainer, VPlotContainer, PlotLabel)
from chaco.tools.api import (ZoomTool, SaveTool, ImageInspectorTool,
        ImageInspectorOverlay, PanTool)

from enthought.enable.component_editor import ComponentEditor

from special_sums import angle_sum, polar_sum

import numpy as np

import urlparse, logging, time, bisect, warnings
from contextlib import closing
from threading import Thread
from collections import deque

try:
    from pydc1394 import camera2 as dc1394
except ImportError, e:
    warnings.warn("pydc1394 cameras not available (%s)" % e)

try:
    import flycapture2 as fc2
except ImportError, e:
    warnings.warn("flycapture2 cameras not available (%s)" % e)


class Capture(HasTraits):
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
        super(Capture, self).__init__(**k)
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
    def _unset_dark(self, val):
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
            logging.debug("1%%>%g, t%s: %g" % (p, s, self.shutter))
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
            logging.debug("saved as %s" % name)
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


class DummyCapture(Capture):
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


class DC1394Capture(Capture):
    cam = Instance(dc1394.Camera)

    pixelsize = Float(3.75)
    maxval = Int((1<<8)-1)
    mode_name = Str("1280x960_Y8")

    def __init__(self, guid, **k):
        self.cam = dc1394.Camera(guid)
        super(DC1394Capture, self).__init__(**k)

    def setup(self):
        self.mode = self.cam.modes_dict[self.mode_name]
        self.cam.mode = self.mode
        self.cam.setup(active=True, mode="manual", absolute=True,
                framerate=None, gain=None, shutter=None) # gamma=None
        self.cam.setup(active=False, exposure=None, brightness=None)
        self.min_shutter = 1e-5 #round(self.cam.shutter.absolute_range[0], 5)
        self.max_shutter = .1 #round(self.cam.shutter.absolute_range[1], 2)
        self.add_trait("shutter", Range(
            self.min_shutter, self.max_shutter,
            self.cam.shutter.absolute))
        self.max_framerate = 10 #round(self.cam.framerate.absolute_range[1], 1)
        self.add_trait("framerate", Range(
            1, #round(self.cam.framerate.absolute_range[0], 1),
            10, #self.max_framerate,
            int(self.cam.framerate.absolute)))
        self.add_trait("gain", Range(
            0, #round(self.cam.gain.absolute_range[0], 0),
            round(self.cam.gain.absolute_range[1], 0),
            self.cam.gain.absolute))
        self.width = int(self.mode.image_size[0])
        self.height = int(self.mode.image_size[1])
        self.cam[0x1098] |= 1<<25 # activate dark current noise reduction

    def start(self):
        try:
            self.cam.start_capture()
        except dc1394.DC1394Error:
            logging.debug("camera capture already running")
        self.cam.start_video()

    def stop(self):
        self.cam.stop_video()
        self.cam.stop_capture()

    @on_trait_change("framerate")
    def _do_framerate(self, val):
        self.cam.framerate.absolute = val

    @on_trait_change("shutter")
    def _do_shutter(self, val):
        self.cam.shutter.absolute = val

    @on_trait_change("gain")
    def _do_gain(self, val):
        self.cam.gain.absolute = val

    def dequeue(self):
        im = None
        im_ = self.cam.dequeue()
        while im_ is not None:
            if im is not None:
                im.enqueue()
                logging.debug("dropped frame")
            im = im_
            im_ = self.cam.dequeue(poll=True)
        return im

    def enqueue(self, im):
        im.enqueue()

    def flush(self):
        self.cam.flush()


class Fc2Capture(Capture):
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


class Process(HasTraits):
    capture = Instance(Capture)

    thread = Instance(Thread)
    active = Bool(False)

    track = Bool(False)
    crops = Int(3) # crop iterations
    rad = Float(3/2.) # crop radius in beam diameters

    background = Range(0., 1., 0.)
    ignore = Range(0., .5, .01)
    include_radius = Float

    x = Float
    y = Float
    t = Float
    e = Float
    a = Float
    b = Float
    d = Float
    black = Float
    peak = Float

    text = Unicode

    grid = None

    def initialize(self):
        self.capture.start()
        im = self.capture.capture()
        self.process(im.copy())
        self.capture.stop()

    def moments(self, im):
        y, x = np.ogrid[:im.shape[0], :im.shape[1]]
        imx, imy = im.sum(axis=0)[None, :], im.sum(axis=1)[:, None]
        m00 = float(imx.sum()) or 1.
        m10, m01 = (imx*x).sum()/m00, (imy*y).sum()/m00
        x, y = x-m10, y-m01
        m20, m02 = (imx*x**2).sum()/m00, (imy*y**2).sum()/m00
        m11 = (im*x*y).sum()/m00
        return m00, m10, m01, m20, m02, m11

    def gauss(self, m00, m20, m02, m11):
        p = m00/(2*np.pi*(m02*m20-m11**2)**.5)
        q = ((m20-m02)**2+4*m11**2)**.5
        a = 2*2**.5*(m20+m02+q)**.5
        b = 2*2**.5*(m20+m02-q)**.5
        t = .5*np.arctan2(2*m11, m20-m02)
        return p, a, b, t

    def do_crop(self, imc, m00, m10, m01, m20, m02, m11):
        if self.ignore > 0: # crop based on encircled energy
            # TODO: ellipse
            re = polar_sum(imc, center=(m01, m10),
                direction="azimuthal", aspect=1., binsize=1.)
            np.cumsum(re, out=re)
            rinc = bisect.bisect(re, (1.-self.ignore)*m00)
            w20 = w02 = rinc
        else: # crop based on 3 sigma region
            w20 = self.rad*4*m20**.5
            w02 = self.rad*4*m02**.5
            rinc = ((w20**2+w02**2)/2)**.5
        lc = int(max(0, m10-w20))
        bc = int(max(0, m01-w02))
        imc = imc[
              int(max(0, m01-w02)):
              int(min(imc.shape[0], m01+w02)),
              int(max(0, m10-w20)):
              int(min(imc.shape[1], m10+w20))]
        return rinc, lc, bc, imc

    def process(self, im):
        im = np.array(im)
        imc = im
        lc, bc = 0, 0
        black = 0
        for i in range(self.crops):
            if self.background > 0:
                blackc = np.percentile(imc, self.background*100)
                imc = imc-blackc
                #np.clip(imc, 0, self.capture.maxval, out=imc)
                black += blackc
            m00, m10, m01, m20, m02, m11 = self.moments(imc)
            if i < self.crops-1:
                rinc, dlc, dbc, imc = self.do_crop(
                        imc, m00, m10, m01, m20, m02, m11)
                lc += dlc
                bc += dbc

        m10 += lc
        m01 += bc
        wp, wa, wb, wt = self.gauss(m00, m20, m02, m11)

        px = self.capture.pixelsize
        l, b, w, h = self.capture.bounds
        
        self.m00 = m00
        self.m20 = m20
        self.m02 = m02
        self.black = black/self.capture.maxval
        self.peak = (wp+black)/self.capture.maxval
        self.x = (m10+l-self.capture.width/2)*px
        self.y = (m01+b-self.capture.height/2)*px
        self.t = np.rad2deg(wt)
        self.a = wa*px
        self.b = wb*px
        self.d = ((self.a**2+self.b**2)/2)**.5
        self.e = wb/wa
        self.include_radius = rinc*px

        self.update_text()

        x = np.arange(l, l+w)-self.capture.width/2
        y = np.arange(b, b+h)-self.capture.height/2
        xbounds = (np.r_[x, x[-1]+1]-.5)*px
        ybounds = (np.r_[y, y[-1]+1]-.5)*px
        imx = im.sum(axis=0) # TODO: available from moments()
        imy = im.sum(axis=1)
        gx = (m00/(2*np.pi*m20)**.5)*np.exp(-(x-self.x/px)**2/(m20*2))
        gy = (m00/(2*np.pi*m02)**.5)*np.exp(-(y-self.y/px)**2/(m02*2))

        #TODO: fix half pixel offset
        xc, yc = m10-im.shape[1]/2., m01-im.shape[0]/2.
        dab = max(abs(np.cos(wt)), abs(np.sin(wt)))
        ima = angle_sum(im, wt, binsize=dab) # minimize binning artefacts
        imb = angle_sum(im, wt+np.pi/2, binsize=dab)
        xcr = (np.cos(wt)*xc+np.sin(wt)*yc)/dab+ima.shape[0]/2.
        ycr = (-np.sin(wt)*xc+np.cos(wt)*yc)/dab+imb.shape[0]/2.
        ima = ima[int(max(0, xcr-self.rad*wa/dab)):
                  int(min(ima.shape[0], xcr+self.rad*wa/dab))]
        imb = imb[int(max(0, ycr-self.rad*wb/dab)):
                  int(min(imb.shape[0], ycr+self.rad*wb/dab))]
        a = np.arange(ima.shape[0])*dab - min(xcr*dab, self.rad*wa)
        b = np.arange(imb.shape[0])*dab - min(ycr*dab, self.rad*wb)
        ga = (m00/(np.pi**.5*wa/2/2**.5))*np.exp(-a**2*(2**.5*2/wa)**2)
        gb = (m00/(np.pi**.5*wb/2/2**.5))*np.exp(-b**2*(2**.5*2/wb)**2)

        upd = dict((
            ("img", im),
            ("xbounds", xbounds), ("ybounds", ybounds),
            ("x", x*px), ("y", y*px),
            ("imx", imx), ("imy", imy),
            ("gx", gx), ("gy", gy),
            ("a", a*px), ("b", b*px),
            ("ima", ima), ("imb", imb),
            ("ga", ga), ("gb", gb),
            ))
        upd.update(self.markers())
        self.data.arrays.update(upd)
        self.data.data_changed = {"changed": upd.keys()}
        if self.grid is not None:
            self.grid.set_data(xbounds, ybounds)

    def markers(self):
        px = self.capture.pixelsize
        ts = np.linspace(0, 2*np.pi, 41)
        ex, ey = self.a/2*np.cos(ts), self.b/2*np.sin(ts)
        t = np.deg2rad(self.t)
        ex, ey = ex*np.cos(t)-ey*np.sin(t), ex*np.sin(t)+ey*np.cos(t)
        k = np.array([-self.rad, self.rad])

        upd = dict((
            ("ell1_x", self.x+ex),
            ("ell1_y", self.y+ey),
            ("ell3_x", self.x+3*ex),
            ("ell3_y", self.y+3*ey),
            ("a_x", self.a*k*np.cos(t)+self.x),
            ("a_y", self.a*k*np.sin(t)+self.y),
            ("b_x", -self.b*k*np.sin(t)+self.x),
            ("b_y", self.b*k*np.cos(t)+self.y),
            ("x0_mark", 2*[self.x]),
            ("xp_mark", 2*[self.x+2*px*self.m20**.5]),
            ("xm_mark", 2*[self.x-2*px*self.m20**.5]),
            ("x_bar", [0, self.m00/(2*np.pi*self.m20)**.5]),
            ("y0_mark", 2*[self.y]),
            ("yp_mark", 2*[self.y+2*px*self.m02**.5]),
            ("ym_mark", 2*[self.y-2*px*self.m02**.5]),
            ("y_bar", [0, self.m00/(2*np.pi*self.m02)**.5]),
            ("a0_mark", 2*[0]),
            ("ap_mark", 2*[self.a/2]),
            ("am_mark", 2*[-self.a/2]),
            ("a_bar", [0, self.m00/(np.pi**.5*self.a/px/2/2**.5)]),
            ("b0_mark", 2*[0]),
            ("bp_mark", 2*[self.b/2]),
            ("bm_mark", 2*[-self.b/2]),
            ("b_bar", [0, self.m00/(np.pi**.5*self.b/px/2/2**.5)]),
        ))
        return upd

    def update_text(self):
        fields = (self.x, self.y,
                self.a, self.b,
                self.t, self.e,
                self.black, self.peak, self.include_radius)

        logging.info("beam: "+(("% 6.4g,"*len(fields)) % fields))

        self.text = (
            u"centroid x: %.4g µm\n"
            u"centroid y: %.4g µm\n"
            u"major 4sig: %.4g µm\n"
            u"minor 4sig: %.4g µm\n"
            u"rotation: %.4g°\n"
            u"ellipticity: %.4g\n"
            u"black-peak: %.4g-%.4g\n"
            u"include radius: %.4g µm\n"
            ) % fields

    def do_track(self):
        r = self.rad
        w, h = self.capture.roi[2:]
        x, y = float(self.x-w/2), float(self.y-h/2)
        #rx, ry = r*4*self.m20**.5, r*4*self.m02**.5
        self.capture.roi = [x, y, w, h]

    @on_trait_change("active")
    def _start_me(self, active):
        if active:
            if self.thread is not None:
                if self.thread.is_alive():
                    logging.warning(
                            "already have a capture thread running")
                    return
                else:
                    self.thread.join()
            self.thread = Thread(target=self.run)
            self.thread.start()
        else:
            if self.thread is not None:
                self.thread.join(timeout=5)
                if self.thread is not None:
                    if self.thread.is_alive():
                        logging.warning(
                                "capture thread did not terminate")
                        return
                    else:
                        logging.warning(
                                "capture thread crashed")
                        self.thread = None
            else:
                logging.debug(
                    "capture thread terminated")

    def run(self):
        logging.debug("start")
        self.capture.start()
        while self.active:
            im = self.capture.capture()
            if im is None:
                continue
            self.process(im.copy())
            if self.track:
                self.do_track()
        logging.debug("stop")
        self.capture.stop()
        self.thread = None

slider_editor=DefaultOverride(mode="slider")


class Bullseye(HasTraits):
    plots = Instance(GridPlotContainer)
    abplots = Instance(VPlotContainer)
    screen = Instance(Plot)
    horiz = Instance(Plot)
    vert = Instance(Plot)
    asum = Instance(Plot)
    bsum = Instance(Plot)

    process = Instance(Process)

    colormap = Enum("gray", "jet", "hot", "prism", "hsv")
    invert = Bool(True)

    label = None
    gridm = None

    traits_view = View(HGroup(VGroup(
        HGroup(
            VGroup(
                Item("object.process.x", label="Centroid x",
                    format_str=u"%.4g µm",
                    tooltip="horizontal beam position relative to chip "
                    "center"),
                Item("object.process.a", label="Major 4sig",
                    format_str=u"%.4g µm",
                    tooltip="major axis beam width 4 sigma ~ 1/e^2 width"),
                Item("object.process.t", label="Rotation",
                    format_str=u"%.4g°",
                    tooltip="angle between horizontal an major axis"),
                #Item("object.process.black", label="Black",
                #    format_str=u"%.4g",
                #    tooltip="background black level"),
            ), VGroup(
                Item("object.process.y", label="Centroid y",
                    format_str=u"%.4g µm",
                    tooltip="vertical beam position relative to chip "
                    "center"),
                Item("object.process.b", label="Minor 4sig",
                    format_str=u"%.4g µm",
                    tooltip="major axis beam width 4 sigma ~ 1/e^2 width"),
                #Item("object.process.d", label="Mean width",
                #    format_str=u"%.4g µm",
                #    tooltip="mean beam width 4 sigma ~ 1/e^2 width"),
                #Item("object.process.e", label="Ellipticity",
                #    format_str=u"%.4g",
                #    tooltip="ellipticity minor-to-major width ratio"),
                #Item("object.process.peak", label="Peak",
                #    format_str=u"%.4g",
                #    tooltip="peak pixel level"),
                Item("object.process.include_radius", label="Include radius",
                    format_str=u"%.4g µm",
                    tooltip="energy inclusion radius according to ignore "
                    "level, used to crop before taking moments"),
            ),
            style="readonly",
        ), VGroup(
            Item("object.process.capture.shutter",
                tooltip="exposure time per frame in seconds"),
            Item("object.process.capture.gain",
                tooltip="analog camera gain in dB"),
            Item("object.process.capture.framerate",
                tooltip="frames per second to attempt, may be limited by "
                "shutter time and processing speed"),
            Item("object.process.capture.average",
                tooltip="number of subsequent images to boxcar average"),
            Item("object.process.background",
                tooltip="background intensity percentile to subtract "
                "from image"),
            Item("object.process.ignore",
                tooltip="fraction of total intensity to ignore for "
                "cropping, determines include radius"),
        ), HGroup(
            Item("object.process.active",
                tooltip="capture and processing running"),
            Item("object.process.capture.auto_shutter",
                tooltip="adjust the shutter time to "
                "yield acceptably exposed frames with peak values "
                "between .25 and .75"),
            Item("object.process.track",
                tooltip="adjust the region of interest to track the "
                "beam center, the size is not adjusted"),
            Item("object.process.capture.dark",
                tooltip="capture a dark image and subtract it from "
                "subsequent images, reset if gain or shutter change"),
        ), HGroup(
            UItem("colormap", tooltip="image colormap"),
            Item("invert", tooltip="invert the colormap"),
        ), UItem("abplots", editor=ComponentEditor(),
                width=-200, height=-300, resizable=False,
                tooltip="line sums (red), moments (blue) and "
                "2-sigma markers (green) along the major and minor axes",
        ),
    ), UItem("plots", editor=ComponentEditor(), width=800,
            tooltip="top right: beam image with 2-sigma and 6-sigma "
            "radius ellipses and axis markers (green). top left and bottom "
            "right: vertial and horizontal line sums (red), moments "
            "(blue) and 2-sigma markers (green). bottom left: beam data "
            "from moments"),
    layout="split",
    ), resizable=True, title=u"Bullseye ― Beam Profiler", width=1000)

    def __init__(self, **k):
        super(Bullseye, self).__init__(**k)
        self.data = ArrayPlotData()
        self.process.data = self.data
        self.process.initialize()

        self.setup_plots()
        self.populate_plots()

    def setup_plots(self):
        self.screen = Plot(self.data,
                resizable="hv", padding=0, bgcolor="lightgray",
                border_visible=False)
        self.screen.index_grid.visible = False
        self.screen.value_grid.visible = False
        px = self.process.capture.pixelsize
        w, h = self.process.capture.width, self.process.capture.height
        # value_range last, see set_range()
        self.screen.index_range.low_setting = -w/2*px
        self.screen.index_range.high_setting = w/2*px
        self.screen.value_range.low_setting = -h/2*px
        self.screen.value_range.high_setting = h/2*px

        self.horiz = Plot(self.data,
                resizable="h", padding=0, height=100,
                bgcolor="lightgray", border_visible=False)
        self.horiz.value_mapper.range.low_setting = \
                -.1*self.process.capture.maxval
        self.horiz.index_range = self.screen.index_range
        self.vert = Plot(self.data, orientation="v",
                resizable="v", padding=0, width=100,
                bgcolor="lightgray", border_visible=False)
        for p in self.horiz, self.vert:
            p.index_axis.visible = False
            p.value_axis.visible = False
            p.index_grid.visible = True
            p.value_grid.visible = False
        self.vert.value_mapper.range.low_setting = \
                -.1*self.process.capture.maxval
        self.vert.index_range = self.screen.value_range

        #self.vert.value_range = self.horiz.value_range

        self.mini = Plot(self.data,
                width=100, height=100, resizable="", padding=0,
                bgcolor="lightgray", border_visible=False)
        self.mini.index_axis.visible = False
        self.mini.value_axis.visible = False
        self.label = PlotLabel(component=self.mini,
                overlay_position="inside left", font="modern 10",
                text=self.process.text)
        self.mini.overlays.append(self.label)

        self.plots = GridPlotContainer(shape=(2,2), padding=0,
                spacing=(5,5), use_backbuffer=True,
                bgcolor="lightgray")
        self.plots.component_grid = [[self.vert, self.screen],
                                     [self.mini, self.horiz ]]

        self.screen.overlays.append(ZoomTool(self.screen,
            x_max_zoom_factor=1e2, y_max_zoom_factor=1e2,
            x_min_zoom_factor=0.5, y_min_zoom_factor=0.5,
            zoom_factor=1.2))
        self.screen.tools.append(PanTool(self.screen))
        self.plots.tools.append(SaveTool(self.plots,
            filename="bullseye.pdf"))

        self.asum = Plot(self.data,
                padding=0, height=100, bgcolor="lightgray",
                title="major axis", border_visible=False)
        self.bsum = Plot(self.data,
                padding=0, height=100, bgcolor="lightgray",
                title="minor axis", border_visible=False)
        for p in self.asum, self.bsum:
            p.value_axis.visible = False
            p.value_grid.visible = False
            p.title_font = "modern 10"
            p.title_position = "left"
            p.title_angle = 90
        # lock scales
        #self.bsum.value_range = self.asum.value_range
        #self.bsum.index_range = self.asum.index_range

        self.abplots = VPlotContainer(padding=20, spacing=20,
                use_backbuffer=True,bgcolor="lightgray",
                fill_padding=True)
        self.abplots.add(self.bsum, self.asum)

    def populate_plots(self):
        self.screenplot = self.screen.img_plot("img",
                xbounds="xbounds", ybounds="ybounds",
                interpolation="nearest",
                colormap=color_map_name_dict[self.colormap],
                )[0]
        self.set_invert()
        self.process.grid = self.screenplot.index
        self.gridm = self.screenplot.index_mapper
        t = ImageInspectorTool(self.screenplot)
        self.screen.tools.append(t)
        self.screenplot.overlays.append(ImageInspectorOverlay(
            component=self.screenplot, image_inspector=t,
            border_size=0, bgcolor="transparent", align="ur",
            tooltip_mode=False, font="modern 10"))

        self.horiz.plot(("x", "imx"), type="line", color="red")
        self.vert.plot(("y", "imy"), type="line", color="red")
        self.horiz.plot(("x", "gx"), type="line", color="blue")
        self.vert.plot(("y", "gy"), type="line", color="blue")
        self.asum.plot(("a", "ima"), type="line", color="red")
        self.bsum.plot(("b", "imb"), type="line", color="red")
        self.asum.plot(("a", "ga"), type="line", color="blue")
        self.bsum.plot(("b", "gb"), type="line", color="blue")

        for p in [("ell1_x", "ell1_y"), ("ell3_x", "ell3_y"),
                ("a_x", "a_y"), ("b_x", "b_y")]:
            self.screen.plot(p, type="line", color="green", alpha=.5)

        for r, s in [("x", self.horiz), ("y", self.vert),
                ("a", self.asum), ("b", self.bsum)]:
            for p in "0 p m".split():
                q = ("%s%s_mark" % (r, p), "%s_bar" % r)
                s.plot(q, type="line", color="green")

    def __del__(self):
        self.close()

    def close(self):
        self.process.active = False

    @on_trait_change("colormap")
    def set_colormap(self):
        p = self.screenplot
        m = color_map_name_dict[self.colormap]
        p.color_mapper = m(p.value_range)
        self.set_invert()
        p.request_redraw()

    @on_trait_change("invert")
    def set_invert(self):
        p = self.screenplot
        if self.invert:
            a, b = self.process.capture.maxval, 0
        else:
            a, b = 0, self.process.capture.maxval
        p.color_mapper.range.low_setting = a
        p.color_mapper.range.high_setting = b

    # TODO: bad layout for one frame at activation, track
    # value_range seems to be updated after index_range, take this
    @on_trait_change("screen.value_range.updated")
    def set_range(self):
        if self.gridm is not None:
            #enforce data/screen aspect ratio 1
            sl, sr, sb, st = self.gridm.screen_bounds
            dl, db = self.gridm.range.low
            dr, dt = self.gridm.range.high
            #dsdx = float(sr-sl)/(dr-dl)
            dsdy = float(st-sb)/(dt-db)
            #dt_new = db+(st-sb)/dsdx
            if dsdy:
                dr_new = dl+(sr-sl)/dsdy
                self.gridm.range.x_range.high_setting = dr_new
        l, r = self.screen.index_range.low, self.screen.index_range.high
        b, t = self.screen.value_range.low, self.screen.value_range.high
        px = self.process.capture.pixelsize
        self.process.capture.roi = [l, b, r-l, t-b]

    @on_trait_change("process.text")
    def set_text(self, value):
        if self.label is not None:
            self.label.text = value


def main():
    import optparse
    p = optparse.OptionParser(usage="%prog [options]")
    p.add_option("-c", "--camera", default="first:",
            help="camera uri (none:, first:, guid:b09d01009981f9) "
                 "[%default]")
    p.add_option("-s", "--save", default="",
            help="save images accordint to strftime() "
                "format string, compressed npz format [%default]")
    p.add_option("-l", "--log",
            help="log output file [stderr]")
    p.add_option("-d", "--debug", default="info",
            help="log level (debug, info, warn, error, "
                "critical, fatal) [%default]")
    opts, args = p.parse_args()
    logging.basicConfig(filename=opts.log,
            level=getattr(logging, opts.debug.upper()),
            format='%(asctime)s %(levelname)s %(message)s')
    scheme, loc, path, query, frag = urlparse.urlsplit(opts.camera)
    if scheme == "guid":
        cam = DC1394Capture(long(path))
    elif scheme == "first":
        cam = DC1394Capture(None)
    elif scheme == "fc2first":
        cam = Fc2Capture(0)
    elif scheme == "fc2index":
        cam = Fc2Capture(int(path))
    elif scheme == "none":
        cam = DummyCapture()
    proc = Process(capture=cam, save_format=opts.save)
    bull = Bullseye(process=proc)
    bull.configure_traits()
    bull.close()

if __name__ == '__main__':
    main()
