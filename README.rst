Bullseye Laser Beam Profiler
======================

Cameras
-------

All monochrome cameras that are supported by libdc1394
(http://damien.douxchamps.net/ieee1394/libdc1394/) or libflycapture2
(http://www.ptgrey.com/support/downloads/download.asp)
are suitable for laser beam profiling. That includes a lot of good and
affordable firewire and USB cameras from several diffeent manufacturers
(Basler, PointGrey, AVT...). 

There are a few limitations:

  * Glass windows: they need to be removed, including the window that is
    typically glued to the chip. Either break it with the chip pointing
    downwards or pull it out while heating the epoxy. This is dangerous
    and will void the cameras warranty. It will also make the chip
    very susceptible to dust and it will age much faster. But it it
    necessary: otherwise fringes will negatively impact image quality.
    Remember that even 1% stray light doe to reflections from glass-air
    interface leads to 40% peak to peak variations in intensity.

  * ND filters -- reflective or volume absorbtive need to be angled
    significantly to keep reflections from interferring at the chip.

  * With front-illuminated silicon chips, wavelengths longer than
    ~1050nm penetrate deeper into the chip and lead to smearing of the
    image along the vertical shift direction.

  * Above 1100nm and below 400nm, the quantum efficiency of the chip
    typically tanks below 5%. Increased powers can destroy the chip
    or bleach it (for UV).

  * Monochrome chips are needed or the Bayer color filter pattern will
    skew results.


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

Chaco, Traits and TraitsUI from enthought ara available prepackaged
under most GNU/Linux systems, but also come included in the highly
recommended Python distributions Python(x,y) (http://www.pythonxy.com)
and the Enthough Python Distribution EPD
(http://www.enthought.com/products/epd.php) for Windows and Mac.

To access cameras via libdc1394, the python wrappers pydc1394 ar needed.
The bazaar branch is at lp:~jordens/pydc1394/work (``bzr branch
lp:~jordens/pydc1394/work``), the Ubuntu/Debian package python-dc1394 is
included in the PPA. From source, use ``sudo python setup.py develop``
to link the source tree into your python installation.

Many cameras can also be accessed using the PointGrey flycapture2
library via the Cython based wrapper pyflycapture2.  Get the source from
the bazaar branch (``bzr branch lp:pyflycapture2``) and install it via
the usual way or use ``sudo python setup.py develop``.


Usage
-----

To quickly check out Bullseye without installing, run it from the source
directory with one of::

    $ python -m bullseye.app
    $ python -m bullseye.app -c fc2first:
    $ python -m bullseye.app -c none:
    $ python -m bullseye.app --help

After installing it via ``sudo python setup.py install`` or linking it
with ``sudo python setup.py develop`` just run::

    $ bullseye
    $ bullseye -c fc2first:
    $ bullseye -c none:
    $ bullseye --help

The ``none:`` scheme uses a dummy noisy gaussian source that also works
without pydc1394 or pyflycapture2 installed.

User Interface
..............

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
markers
horizonatal and vertical sum
markers
major and minor sum
markers
text field
zooming and panning
ctrl-s to save pdf as ``bullseye.pdf``
save_format
csv output with --debug info and log filename
