"""TrackUtils.py
"""

import json
import argparse
import biglab.track
import struct, socket, pyroute2

def pton(addr):
    buf = socket.inet_pton(socket.AF_INET6, addr)
    ql = struct.unpack("!QQ", buf)
    return (ql[0]<<64) | ql[1]

def ntop(addrInt):
    mask = (1<<64)-1
    ql = (addrInt>>64, addrInt & mask,)
    buf = struct.pack("!QQ", addrInt>>64, addrInt&mask)
    return socket.inet_ntop(socket.AF_INET6, buf)

def mton(macStr):
    macBytes = [int(x, 16) for x in macStr.split(':')]
    macBytes[3:3] = [0xff, 0xfe]
    macBytes[0] |= 0x2
    buf = struct.pack("BBBBBBBB", *macBytes)
    ql = struct.unpack("!Q", buf)
    return ql[0]

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

IPR = pyroute2.IPRoute()

def get_links():
    links = {}
    for link in IPR.get_links():
        links[link['index']] = dict(link['attrs'])
    return links

def getDefaultV6Intf():
    localMask = pton("fe80::")
    links = get_links()
    for route in IPR.get_routes():
        if route['family'] != socket.AF_INET6: continue
        if route['dst_len'] < 64: continue
        attrs = dict(route['attrs'])
        dstAddr = pton(attrs['RTA_DST'])
        if dstAddr & localMask != localMask: continue
        intf = links[attrs['RTA_OIF']]
        return intf['IFLA_IFNAME']

def getDefaultV6Addr():
    localMask = pton("fe80::")
    links = get_links()
    for route in IPR.get_routes():
        if route['family'] != socket.AF_INET6: continue
        if route['dst_len'] < 64: continue
        attrs = dict(route['attrs'])
        dstAddr = pton(attrs['RTA_DST'])
        if dstAddr & localMask != localMask: continue
        intfIndex = attrs['RTA_OIF']
        for addrData in IPR.get_addr(index=intfIndex, family=socket.AF_INET6):
            attrs = dict(addrData['attrs'])
            addr = attrs['IFA_ADDRESS']
            addrInt = pton(addr)
            if addrInt & localMask == localMask:
                return addr
