#!/usr/bin/env python
import argparse
import logging
import os
import socket
from functools import partial

from actorcore.Actor import Actor
from astropy.io import fits
from ginga.util import grc
from ics.utils.sps.spectroIds import getSite
from twisted.internet import reactor


class GingaActor(Actor):
    host2name = {'PFS-WS1': 'gingaws1', 'PFS-WS2': 'gingaws2', 'cappy': 'gingacappy', 'pcp-pfs2': 'gingapcp2',
                 'actors-ics': 'gingaactors'}

    def __init__(self, name, productName=None, configFile=None, logLevel=30):
        # This sets up the connections to/from the hub, the logger, and the twisted reactor.
        #
        try:
            name = GingaActor.host2name[socket.gethostname()]
        except KeyError:
            name = 'ginga'

        specIds = list(range(1, 5))
        cams = [f'b{specId}' for specId in specIds] + [f'r{specId}' for specId in specIds]

        self.site = getSite()

        Actor.__init__(self, name,
                       productName=productName,
                       configFile=configFile, modelNames=['ccd_%s' % cam for cam in cams] + ['sac', 'drp'])

        self.rcHost = 'localhost'
        self.rcPort = None
        self.gingaViewer = self.startViewer(rcPort=9000)

        reactor.callLater(5, partial(self.attachCallbacks, cams))

    def startViewer(self, cmd=None, rcPort=None):
        """"""
        cmd = self.bcast if cmd is None else cmd
        self.rcPort = rcPort if rcPort is not None else self.rcPort + 1
        cmd.inform(f'text="starting RC server on {self.rcHost}:{self.rcPort}')
        return grc.RemoteClient(self.rcHost, self.rcPort)

    def attachCallbacks(self, cams):
        self.logger.info('attaching callbacks cams=%s' % (','.join(cams)))
        for cam in cams:
            self.models['ccd_%s' % cam].keyVarDict['filepath'].addCallback(partial(self.ccdFilepath, cam),
                                                                           callNow=False)

        self.models['sac'].keyVarDict['filepath'].addCallback(self.sacFilepath, callNow=False)
        self.models['drp'].keyVarDict['detrend'].addCallback(self.drpFilepath, callNow=False)

    def sacFilepath(self, keyvar):
        # ignoring if not at LAM.
        if self.site != 'L':
            return

        filepath = keyvar.getValue()
        absPath = os.path.join(*filepath)
        self.loadHdu(absPath, chname='SAC')

    def ccdFilepath(self, cam, keyvar):
        # ignoring if not at LAM.
        if self.site != 'L':
            return

        [root, night, fname] = keyvar.getValue()
        args = [root, night, 'sps', fname]
        filepath = os.path.join(*args)
        self.loadHdu(filepath, chname='%s_RAW' % cam.upper(), hdu=1)

    def drpFilepath(self, keyvar):

        filepath = keyvar.getValue()
        folder, fname = os.path.split(filepath)
        fname, __ = fname.split('.fits')
        cam = fname[-2:]

        self.loadHdu(filepath, chname='%s_DETREND' % cam.upper(), hdu=1)

    def loadHdu(self, path, chname, hdu=0):
        channel = self.connectChannel(chname=chname)
        hdulist = fits.open(path, 'readonly')
        filepath, fname = os.path.split(path)
        channel.load_hdu(fname, hdulist, hdu)
        self.logger.info('channel : %s loading fits from : %s hdu : %i', chname, path, hdu)

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
    args = parser.parse_args()

    theActor = GingaActor('ginga',
                          productName='gingaActor',
                          configFile=args.config,
                          logLevel=args.logLevel)
    theActor.run()


if __name__ == '__main__':
    main()
