#!/usr/bin/env python
import argparse
import logging
from functools import partial

from actorcore.Actor import Actor
from astropy.io import fits
from ginga.util import grc


class GingaActor(Actor):
    def __init__(self, name, productName=None, configFile=None, logLevel=30, cams=''):
        # This sets up the connections to/from the hub, the logger, and the twisted reactor.
        #
        cams = cams.split(',')

        Actor.__init__(self, name,
                       productName=productName,
                       configFile=configFile, modelNames=['ccd_%s' % cam for cam in cams])

        host = 'localhost'
        port = 9000
        self.gingaViewer = grc.RemoteClient(host, port)

        for cam in cams:
            self.models['ccd_%s' % cam].keyVarDict['filepath'].addCallback(partial(self.newFilepath, cam),
                                                                           callNow=False)

    def newFilepath(self, cam, keyvar):
        filepath = keyvar.getValue()
        absPath = '/'.join([filepath[0], 'pfs', filepath[1], filepath[2]])
        self.loadHdu(absPath, chname='%s_RAW' % cam.upper())

    def loadHdu(self, path, chname):
        channel = self.connectChannel(chname=chname)
        hdulist = fits.open(path, 'readonly')
        channel.load_hdu(path[-17:], hdulist, 0)
        self.logger.info('channel : %s loading fits from : %s hdu : %i', chname, path, 0)

    def connectChannel(self, chname):

        try:
            channel = self.gingaViewer.channel(chname)

        except:
            gingaShell = self.gingaViewer.shell()
            gingaShell.add_channel(chname)
            channel = self.gingaViewer.channel(chname)

        return channel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=None, type=str, nargs='?',
                        help='configuration file to use')
    parser.add_argument('--logLevel', default=logging.INFO, type=int, nargs='?',
                        help='logging level')
    parser.add_argument('--name', default='ginga', type=str, nargs='?',
                        help='identity')
    parser.add_argument('--cams', default='r1', type=str, nargs='?',
                        help='cams')
    args = parser.parse_args()

    theActor = GingaActor(args.name,
                          productName='gingaActor',
                          configFile=args.config,
                          logLevel=args.logLevel,
                          cams=args.cams)
    theActor.run()


if __name__ == '__main__':
    main()
