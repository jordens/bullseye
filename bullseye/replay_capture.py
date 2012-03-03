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

from traits.api import Str

import numpy as np
import glob, itertools

from .capture import BaseCapture

class ReplayCapture(BaseCapture):
    replay_glob = Str

    def __init__(self, replay_glob, **k):
        self.replay_glob = replay_glob
        super(ReplayCapture, self).__init__(**k)

    def setup(self):
        names = glob.glob(self.replay_glob)
        names.sort()
        self.names = itertools.cycle(names)
        self.height, self.width = self.dequeue().shape

    def dequeue(self):
        return np.load(self.names.next())["arr_0"]
