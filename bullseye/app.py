from traits.trait_base import ETSConfig
ETSConfig.toolkit = "qt4"
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
    p.add_option("-c", "--camera", default="any:",
            help="camera uri (none:, any:, dc1394://guid/b09d01009981f9, "
                 "fc2://index/1, replay://glob/beam*.npz) [%default]")
    p.add_option("-s", "--save", default=None,
            help="save images accordint to strftime() "
                "format string (e.g. 'beam_%Y%m%d%H%M%S.npz'), "
                "compressed npz format [%default]")
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
    if scheme == "dc1394":
        from .dc1394_capture import DC1394Capture
        if loc == "guid":
            cam = DC1394Capture(long(path[1:], base=16))
    elif scheme == "fc2":
        from .flycapture2_capture import Fc2Capture
        if loc == "index":
            cam = Fc2Capture(int(path[1:]))
    elif scheme == "replay":
        from .replay_capture import ReplayCapture
        if loc == "glob":
            cam = ReplayCapture(path[1:])
    elif scheme == "none":
        from .capture import DummyCapture
        cam = DummyCapture()
    elif scheme == "any":
        try:
            from .dc1394_capture import DC1394Capture
            cam = DC1394Capture()
        except Exception, e:
            logging.debug("dc1394 error: %s", e)
            try:
                from .flycapture2_capture import Fc2Capture
                cam = Fc2Capture()
            except Exception, e:
                logging.debug("flycapture2 error: %s", e)
                from .capture import DummyCapture
                cam = DummyCapture()
    logging.debug("running with capture device: %s", cam)
    if opts.save:
        cam.save_format = opts.save
    proc = Process(capture=cam)
    bull = Bullseye(process=proc)
    bull.configure_traits()
    bull.close()

if __name__ == "__main__":
    main()
