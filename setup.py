#!/usr/bin/python
# -*- coding: utf8 -*-
#
#   bullseye - ccd laser beam profilers (pydc1394 + chaco)
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


from setuptools import setup, find_packages

setup(
        name = "bullseye",
        version = "0.1.1+dev",
        description = "laser beam profiler",
        long_description = """
            Bullseye is a laser beam analysis application. Images can be
            acquired from any USB or Firewire camera using the DC1394
            standard supported by pydc1394 or pyflycapture2 from
            pointgrey.  The beam analysis mostly adheres to ISO-11146
            and determines centroid, 4-sigma width (~1/e^2 intensity
            width), rotation and ellipticity. The user interface is
            build on enthought/{traits, chaco}.""",
        author = "Robert Jordens",
        author_email = "robert@joerdens.org",
        url = "http://launchpad.net/pybullseye",
        license = "GPLv3+",
        keywords = "laser beam profiler ccd camera gaussian",
        install_requires = [
            "numpy", "traits>=4", "chaco", "traitsui"],
        extras_require = {
            "pydc1394": ["pydc1394"],
            "flycapture2": ["pyflycapture2"],
            },
        #dependency_links = [],
        packages = find_packages(),
        #namespace_packages = [],
        #test_suite = "bullseye.tests.test_all",
        entry_points = {
            "gui_scripts": ["bullseye = bullseye.app:main"],
            },
        include_package_data = True,
        classifiers = [f.strip() for f in """
            Development Status :: 4 - Beta
            Environment :: X11 Applications :: GTK
            Environment :: X11 Applications :: Qt
            Intended Audience :: Science/Research
            Intended Audience :: Telecommunications Industry
            License :: OSI Approved :: GNU General Public License (GPL)
            Operating System :: OS Independent
            Programming Language :: Python :: 2
            Topic :: Multimedia :: Graphics :: Capture :: Digital Camera
            Topic :: Multimedia :: Video :: Capture
            Topic :: Multimedia :: Video :: Display
            Topic :: Scientific/Engineering :: Physics
        """.splitlines() if f.strip()],
        )
