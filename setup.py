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


from setuptools import setup, find_packages

setup(
        name = "bullseye",
        description = "laser beam profiler",
        long_description = """
            Bullseye is a laser beam analysis application. Images can be
            acquired from any USB or Firewire camera using the DC1394
            standard supported by pydc1394 or pyflycapture2 from
            pointgrey.  The beam analysis mostly adheres to ISO-11146
            and determines centroid, 4-sigma width (~1/e^2 intensity
            width), rotation and ellipticity. The user interface is
            build on enthought/{traits, chaco}.""",
        version = "0.1.1",
        author = "Robert Jordens",
        author_email = "jordens@phys.ethz.ch",
        url = "http://launchpad.net/pybullseye",
        license = "GPLv3+",
        install_requires = [
            "numpy", "scipy", "traits>=4", "chaco", "traitsui"],
        extras_require = {
            "pydc1394": ["pydc1394"],
            "flycapture2": ["pyflycapture2"],
            },
        dependency_links = [],
        packages = find_packages(),
        namespace_packages = [],
        #test_suite = "bullseye.tests.test_all",
        entry_points = {
            "gui_scripts": [
                "bullseye = bullseye.app:main"
                ],
            },
        include_package_data = True,
        )
