Bullseye Laser Beam Profiler
============================

Bullseye is a laser beam analysis application. Images can be acquired
from any USB or Firewire camera using the DC1394 standard supported by
pydc1394 or pyflycapture2 from pointgrey.  The beam analysis mostly
adheres to ISO-11146 and determines centroid, 4-sigma width (~1/e^2
intensity width), rotation and ellipticity. The user interface is build
on enthought/{traits, chaco}.

Cameras
-------

All monochrome cameras that are supported by libdc1394
(http://damien.douxchamps.net/ieee1394/libdc1394/) or libflycapture2
(http://www.ptgrey.com/support/downloads/download.asp)
are suitable for laser beam profiling. That includes a lot of good and
affordable firewire and USB cameras from several different manufacturers
(http://damien.douxchamps.net/ieee1394/cameras/). 

There are a few limitations:

  * Glass windows: they need to be removed, including the window that is
    typically glued to the chip. Either break it with the chip pointing
    downwards or pull it out while heating the epoxy. This is dangerous
    and will void the camera's warranty. It will also make the chip
    very susceptible to dust and it will age much faster. But it it
    necessary: otherwise fringes will negatively impact image quality.
    Remember that even 1% stray light due to reflections from glass-air
    interfaces leads to 40% peak to peak variations in intensity.

  * ND filters -- reflective or volume absorptive need to be angled
    significantly to keep reflections from interfering at the chip.
    Those filters also need to be of good quality to not distort the
    beam.

  * With front-illuminated silicon chips, wavelengths longer than
    ~1050nm penetrate deeper into the chip and lead to long living
    excitations and smearing of the image along the vertical shift
    direction.

  * Above 1100nm and below 400nm, the quantum efficiency of Silicon
    chips is typically below 5%. Increased powers can destroy the chip
    or bleach it.

  * Monochrome chips are recommended. Otherwise the Bayer color filter
    pattern will skew results.


Installation
------------

Ubuntu/Debian
..............

Get the package from the PPA::

    $ sudo add-apt-repository ppa:jordens/bullseye-trunk
    $ sudo apt-get update
    $ sudo apt-get install python-bullseye

PyPi
....

Use either ``easy_install`` or ``pip`` to get and install the required
packages from the python package index.

Source
......

Chaco, Traits and TraitsUI from enthought (http://code.enthought.com/)
are available prepackaged under most GNU/Linux systems, but also come
included in the highly recommended Python distributions Python(x,y)
(http://www.pythonxy.com) and the Enthough Python Distribution EPD
(http://www.enthought.com/products/epd.php) for Windows and Mac.

To access cameras via libdc1394, the python wrappers pydc1394
(https://launchpad.net/pydc1394) are needed.  The bazaar branch is at
``lp:~jordens/pydc1394/work`` (``bzr branch
lp:~jordens/pydc1394/work``), the Ubuntu/Debian package python-dc1394 is
included in the PPA. From source, use ``sudo python setup.py develop``
to link the source tree into your python installation.

Many cameras can also be accessed using the PointGrey flycapture2
library via the Cython based wrapper pyflycapture2
(https://launchpad.net/pyflycapture2). Download the library and headers
from PointGrey (http://www.ptgrey.com/support/downloads/download.asp
account required, closed source) and install them. Get the wrapper
source from the bazaar branch (``bzr branch lp:pyflycapture2``) and
install it via the usual way or use ``sudo python setup.py develop``.
This needs ``cython``.

Usage
-----

To quickly check out Bullseye without installing, run it from the source
directory with one of::

    $ python -m bullseye.app
    $ python -m bullseye.app -camera fc2://index/0
    $ python -m bullseye.app -camera none:
    $ python -m bullseye.app --help

After installing it via ``sudo python setup.py install`` or linking it
with ``sudo python setup.py develop`` just run one of::

    $ bullseye
    $ bullseye -camera fc2://index/0
    $ bullseye -camera none:
    $ bullseye --help

The ``none:`` scheme uses a dummy noisy gaussian source that also works
without pydc1394 or pyflycapture2 installed.

User Interface
..............

Beam size definition
http://www.rp-photonics.com/spotlight_2007_07_11.html
ISO-11146 (moments) versus least squares fit versus clipping
http://www.rp-photonics.com/beam_radius.html
offset control via background percentile, energy inclusion radius,
roi, average, and dark frame subtraction

camera settings
shutter
auto shutter
gain
framerate

processing settings
dark
average
background
ignore
track

image
colormap
http://www.research.ibm.com/people/l/lloydt/color/color.HTM
http://dx.doi.org/10.1109/MCG.2007.323435
http://www.jwave.vt.edu/~rkriz/Projects/create_color_table/color_07.pdf
for an accessible copy
http://www.slideshare.net/ptomato/20101007-lunch-meeting

green 2sigma, 6sigma radius markers
horizonatal and vertical sum plot and gauss via moments
green markers for 2sigma
major and minor sum and gauss via moments
green markers for 2sigma
text field
zooming and panning with mouse dragging and mousewheel
ctrl-s to save pdf of main screen as ``bullseye.pdf``
save images: --save_format
replay with -camera replay://glob/path*.npz
csv output with --debug info and --log log filename
