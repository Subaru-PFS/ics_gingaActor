#!/usr/bin/env python

from actorcore.Actor import Actor
from astropy.io import fits
from ginga.util import grc


class GingaActor(Actor):
    def __init__(self, name, productName=None, configFile=None, debugLevel=30):
        # This sets up the connections to/from the hub, the logger, and the twisted reactor.
        #
        Actor.__init__(self, name,
                       productName=productName,
                       configFile=configFile, modelNames=['ccd_r1'])

        self.gingaViewer = None
        self.models['ccd_r1'].keyVarDict['filepath'].addCallback(self.newFilepath, callNow=False)

    def newFilepath(self, keyvar):
        filepath = keyvar.getValue()
        absPath = '/'.join([filepath[0], 'pfs', filepath[1], filepath[2]])
        self.loadImage(absPath)

    def loadImage(self, path, chname='R1_RAW'):
        channel = self.connectViewer(chname=chname)
        hdulist = fits.open(path, "readonly")
        channel.load_hdu(path[-17:], hdulist, 0)

    def connectViewer(self, chname, host='localhost', port=9000):
        if self.gingaViewer is None:
            gingaViewer = grc.RemoteClient(host, port)
            gingaShell = gingaViewer.shell()
            gingaShell.add_channel(chname)
            self.gingaViewer = gingaViewer

        return self.gingaViewer.channel(chname)


def main():
    actor = GingaActor('ginga', productName='gingaActor')
    actor.run()


if __name__ == '__main__':
    main()
