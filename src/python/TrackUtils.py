"""TrackUtils.py
"""

import json
import argparse
import biglab.track

from IpUtils import ntop, pton, mton

class BigTrack(biglab.track.BigTrack):

    def __init__(self):
        biglab.track.BigTrack.__init__(self)
        ns = argparse.Namespace()
        ns.username = ns.port = ns.server = None
        self.Init(ns)

    def getSwitch(self, switch):
        url = "show/%s/" % switch
        data = json.loads(self._BigTrack__restGet(url))
        if not data: return None
        return data[0]

    def getSwitchV6Address(self, switch):
        data = self.getSwitch(switch)
        if data is None: return None
        netInt = pton("fe80::")
        hostInt = mton(data['Ethernet'])
        return ntop(netInt | hostInt)
