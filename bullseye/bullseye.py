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

from traits.api import (HasTraits, Enum, Bool,
        Instance, Delegate, on_trait_change)

from traitsui.api import (View, Item, UItem,
        HGroup, VGroup, DefaultOverride)

from chaco.api import (Plot, ArrayPlotData, color_map_name_dict,
        GridPlotContainer, VPlotContainer, PlotLabel)
from chaco.tools.api import (ZoomTool, SaveTool, ImageInspectorTool,
        ImageInspectorOverlay, PanTool)

from enthought.enable.component_editor import ComponentEditor

from .process import Process

slider_editor = DefaultOverride(mode="slider")


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

        self.plots = GridPlotContainer(shape=(2, 2), padding=0,
                spacing=(5, 5), use_backbuffer=True,
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
