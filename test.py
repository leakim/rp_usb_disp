#!/usr/bin/env python
import usb
import types
import struct
from time import sleep

VENDOR_ID  = 0xfccf
PRODUCT_ID = 0xa001

def print_dev(dev):
    print "Device:", dev.filename
    print "  Device class:",dev.deviceClass
    print "  Device sub class:",dev.deviceSubClass
    print "  Device protocol:",dev.deviceProtocol
    print "  Max packet size:",dev.maxPacketSize
    print "  idVendor: %d (0x%04x)" % (dev.idVendor, dev.idVendor)
    print "  idProduct: %d (0x%04x)" % (dev.idProduct, dev.idProduct)
    print "  Device Version:",dev.deviceVersion
    for config in dev.configurations:
        print "  Configuration:", config.value
        print "    Total length:", config.totalLength
        print "    selfPowered:", config.selfPowered
        print "    remoteWakeup:", config.remoteWakeup
        print "    maxPower:", config.maxPower
        for intf in config.interfaces:
            print "    Interface:",intf[0].interfaceNumber
            for alt in intf:
                print "    Alternate Setting:",alt.alternateSetting
                print "      Interface class:",alt.interfaceClass
                print "      Interface sub class:",alt.interfaceSubClass
                print "      Interface protocol:",alt.interfaceProtocol
                for ep in alt.endpoints:
                    print "      Endpoint:",hex(ep.address)
                    print "        Type:",ep.type
                    print "        Max packet size:",ep.maxPacketSize
                    print "        Interval:",ep.interval

def find_disp(vid = VENDOR_ID, pid = PRODUCT_ID):
    for bus in usb.busses():
        devices = bus.devices
        for dev in devices:
            if dev.idVendor == vid and dev.idProduct == pid:
                return dev

def find_endp(dev):
    for config in dev.configurations:
        for intf in config.interfaces:
            for alt in intf:
                for ep in alt.endpoints:
                    if ep.type == 2: # bulk
                        if ep.address == 0x1L:
                            return ep, intf[0].interfaceNumber

def rgb565(r=0, g=0, b=0):
    if r > 0x1f: r = 0x1f
    if g > 0x3f: g = 0x3f
    if b > 0x1f: b = 0x1f
    return struct.pack('<H', r + (g<<5) + (b<<11))

def rgb555(r=0, g=0, b=0):
    return rgb565(r=r,g=(g<<1), b=b)

def fill_rgb(color):
    return struct.pack('<B', 0x80 + 0x40 + 1) + color

OP_COPY = 0
OP_XOR  = 1
OP_OR   = 2
OP_AND  = 3

def rect(left, top, w, h, color, op):
    right = left + w
    bottom =  top + h
    cmd = struct.pack('<B', 0x80 + 0x40 + 3)
    rect = struct.pack('<HHHH', left, top, right, bottom)
    return cmd + rect + color + chr(op)

class usb_disp:
    def __init__(self):
        self.dev = None
        dev = find_disp()
        if not dev: return
        print_dev(dev)
        ep, intf = find_endp(dev)
        odev = dev.open()
        odev.claimInterface(intf)
        self.dev, self.intf, self.ep = odev, intf, ep

    def close(self):
        if not self.dev: return
        self.dev.releaseInterface()

    def send(self, cmd):
        if not self.dev: return
        self.dev.bulkWrite(self.ep.address, cmd)

colors = [
    rgb555(
        r=0x1f,
        g=0,
        b=0),
    rgb555(
        r=0,
        g=0x1f,
        b=0),
    rgb555(
        r=0,
        g=0,
        b=0x1f),
    rgb555(
        r=0,
        g=0,
        b=0),
    rgb555(
        r=0x1f,
        g=0x1f,
        b=0x1f),
    rgb555(
        r=0x1f,
        g=0x1f,
        b=0),
    rgb555(
        r=0x1f,
        g=0x1f,
        b=0),
    rgb555(
        r=0x1f,
        g=0,
        b=0x1f)
]

d = usb_disp()

for color in colors:
    d.send( fill_rgb(color) )
    sleep(0.5)

for i in xrange(0,31):
    d.send( fill_rgb( rgb555( r=i, g=i, b=i) ) )
    sleep(0.010)
    print "%x" % i

d.send( fill_rgb( rgb555( r=0, g=0, b=0) ) )
d.send( rect( 100, 50, 200, 80, rgb555(0,0,16), OP_COPY) )
d.send( rect( 150, 100, 50, 100, rgb555(16,0,0), OP_OR) )
sleep(1)

d.close()
