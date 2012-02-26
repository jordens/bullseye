#!/usr/bin/python

from setuptools import setup, find_packages
from glob import glob

setup(
        name = "bullseye",
        version = "0.1",
        author = "Robert Jordens",
        author_email = "jordens@phys.ethz.ch",
        url = "http://launchpad.net/bullseye",
        description = "laser beam profiler",
        license = "GPLv3+",
        install_requires = [
            "numpy", "scipy", "traits>=4", "chaco"],
        extras_require = {
            "pydc1394": ["pydc1394"],
            "flycapture2": ["pyflycapture2"],
            },
        dependency_links = [],
        packages = find_packages(),
        namespace_packages = [],
        #test_suite = "bullseye.tests.test_all",
        #scripts = glob("notebooks/*.py"),
        entry_points = {
            "console_scripts": [
                #"foo = my_package.some_module:main_func",
                ],
            "gui_scripts": [
                "bullseye = bullseye.bullseye.main"
                ],
            },
        include_package_data = True,
        #package_data = {"": ["notebooks/*.ipynb"]},
        )
