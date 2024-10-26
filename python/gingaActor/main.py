#!/usr/bin/env python
import argparse
import logging
import os
import re
import socket
from functools import partial

from actorcore.Actor import Actor
from astropy.io import fits
from ginga.util import grc
from ics.utils.sps.spectroIds import getSite


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
        vis = [f'b{specId}' for specId in specIds] + [f'r{specId}' for specId in specIds]
        nir = [f'n{specId}' for specId in specIds]

        self.ccds = [f'ccd_{cam}' for cam in vis]
        self.hxs = [f'hx_{cam}' for cam in nir]

        self.site = getSite()

        Actor.__init__(self, name,
                       productName=productName,
                       configFile=configFile, modelNames=self.ccds + self.hxs + ['sac', 'drp'])

        self.everConnected = False
        self.rcHost = 'localhost'
        self.rcPort = None
        self.gingaViewer = self.startViewer(rcPort=9000)

    def connectionMade(self):
        """Called when the actor connection has been established: wire in callbacks."""
        if self.everConnected is False:

            for ccd in self.ccds:
                self.models[ccd].keyVarDict['filepath'].addCallback(partial(self.ccdFilepath, ccd), callNow=False)
                self.logger.info(f'{ccd}.filepath callback attached')

            self.models['sac'].keyVarDict['filepath'].addCallback(self.sacFilepath, callNow=False)
            self.models['drp'].keyVarDict['detrend'].addCallback(self.drpFilepath, callNow=False)

            self.everConnected = True

    def startViewer(self, cmd=None, rcPort=None):
        """"""
        cmd = self.bcast if cmd is None else cmd
        self.rcPort = rcPort if rcPort is not None else self.rcPort + 1
        cmd.inform(f'text="starting RC server on {self.rcHost}:{self.rcPort}')
        return grc.RemoteClient(self.rcHost, self.rcPort)

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

    def drpFilepath(self, keyVar):
        """
        Process the detrended image filepath and load the relevant HDU into the Ginga viewer.

        Parameters
        ----------
        keyVar : KeyVar
            KeyVar object containing the filepath of the detrended image.
        """
        # Extract the filepath from the keyVar object.
        filepath = keyVar.getValue()

        # Split the filepath to get the directory and filename.
        rootDir, filename = os.path.split(filepath)

        # Get the channel name based on the filename pattern.
        channelName = self._getChannelName(filename)

        # Load the HDU of the fits file into the appropriate Ginga channel.
        self.loadHdu(filepath, chname=channelName, hdu=1)

    def _getChannelName(self, filename):
        """
        Extract the camera name (channel) from the filename.

        Parameters
        ----------
        filename : str
            Name of the file to extract the channel from.

        Returns
        -------
        str
            Capitalized channel name (e.g., 'B4'), or 'Image' if not found.
        """
        pattern = r'_([brmn]\d)_'  # Pattern to capture camera names like 'b4', 'r1', etc.
        camera = re.search(pattern, filename)

        # Return the matched channel name, or 'Image' if not found.
        return camera.group(1).capitalize() if camera else 'Image'

    def loadHdu(self, path, chname, hdu=0):
        """
        Load a specific HDU from the fits file into the Ginga viewer.

        Parameters
        ----------
        path : str
            Path to the fits file.
        chname : str
            Name of the Ginga channel to load the HDU into.
        hdu : int, optional
            HDU index to load from the fits file, by default 0.
        """
        # Connect to the specified Ginga channel.
        channel = self.connectChannel(chname=chname)

        # Open the fits file in read-only mode.
        hdulist = fits.open(path, 'readonly')

        # Extract the filename from the full path.
        _, filename = os.path.split(path)

        # Load the HDU into the Ginga channel.
        channel.load_hdu(filename, hdulist, hdu)

        # Log the loaded file and HDU information.
        self.logger.info('Channel: %s loading fits from: %s hdu: %i', chname, path, hdu)

    def connectChannel(self, chname):
        """
        Connect to a Ginga viewer channel or create a new one if it does not exist.

        Parameters
        ----------
        chname : str
            Name of the channel to connect to.

        Returns
        -------
        GingaChannel
            The connected or newly created Ginga channel.
        """
        try:
            # Try to connect to an existing Ginga channel.
            channel = self.gingaViewer.channel(chname)

        except Exception:
            # If the channel does not exist, create a new one.
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
