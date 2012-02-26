from traits.trait_base import ETSConfig
#ETSConfig.toolkit = "qt4"
# fix window color on unity
if ETSConfig.toolkit == "wx":
    from traitsui.wx import constants
    constants.WindowColor = constants.wx.NullColor

import optparse, logging, urlparse

#from .capture import BaseCapture, DummyCapture
from .process import Process
from .bullseye import Bullseye


def main():
    p = optparse.OptionParser(usage="%prog [options]")
    p.add_option("-c", "--camera", default="first:",
            help="camera uri (none:, first:, guid:b09d01009981f9, "
                 "fc2first:, fc2index:0) "
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
        from .dc1394_capture import DC1394Capture
        cam = DC1394Capture(long(path))
    elif scheme == "first":
        from .dc1394_capture import DC1394Capture
        cam = DC1394Capture(None)
    elif scheme == "fc2first":
        from .flycapture2_capture import Fc2Capture
        cam = Fc2Capture(0)
    elif scheme == "fc2index":
        from .flycapture2_capture import Fc2Capture
        cam = Fc2Capture(int(path))
    elif scheme == "none":
        from .capture import DummyCapture
        cam = DummyCapture()
    proc = Process(capture=cam, save_format=opts.save)
    bull = Bullseye(process=proc)
    bull.configure_traits()
    bull.close()

if __name__ == "__main__":
    main()
