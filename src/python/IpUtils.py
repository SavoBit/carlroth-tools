"""IpUtils.py

Miscellaneous IP utilities.
"""

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

def getV6AddrFromMac(mac, intf=None):
    """See ztn.MdnsDiscovery.Server6.zone()."""
    macBytes = mac.split(':')
    macBytes = [int(x, 16) for x in macBytes]
    macBytes[0] ^= 0x02
    intf = intf or getDefaultV6Intf()
    macArgs = macBytes + [intf,]
    return ("fe80::%02x%02x:%02xff:fe%02x:%02x%02x%%%s"
            % tuple(macArgs))
