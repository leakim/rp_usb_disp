#!/usr/bin/env python
# -*- coding: utf-8 -*-

import usb
import types
import struct
from time import sleep

VENDOR_ID  = 0xfccf
PRODUCT_ID = 0xa001

WIDTH  = 320
HEIGHT = 240

CMD_START = (1<<7)
CMD_CLEAR = (1<<6)

CMD_FILL = 1
CMD_IMG  = 2
CMD_RECT = 3
CMD_COPY = 4

OP_COPY = 0
OP_XOR  = 1
OP_OR   = 2
OP_AND  = 3


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

def rect(left, top, w, h, color, op):
    right = left + w
    bottom =  top + h
    data = struct.pack('<HHHH', left, top, right, bottom)
    return [CMD_RECT, data + color + chr(op)]

class Img:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.pixels = [rgb565(0, 0, 0)]*w*h

    def pset(self, i, r, g, b):
        self.pixels[i] = rgb555(r, g, b)

    def pack(self, x, y, op):
        h = struct.pack('<HHHH', x, y, self.w, self.h)
        # data is 16 bit/pix ; N=w*h
        data = b''
        for p in self.pixels:
            data += p
        return [CMD_IMG, h + chr(op), data]

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

    def send(self, cmd_id, cmd, payload=b'', PKT_MAX = 63):
        if not self.dev: return
        h = chr(CMD_START | CMD_CLEAR | cmd_id)
        o = PKT_MAX - len(cmd)
        pkt = h + cmd + payload[0:o]
        self.dev.bulkWrite(self.ep.address, pkt)
        h = chr(cmd_id)
        for i in xrange(o , len(payload), PKT_MAX):
            pkt = h + payload[i:i + PKT_MAX]
            self.dev.bulkWrite(self.ep.address, pkt)

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

#####################################################################

for color in colors:
    d.send( CMD_FILL, color)
    sleep(0.5)

for i in xrange(0,31):
    d.send( CMD_FILL, rgb555(r=i, g=i, b=i) )
    sleep(0.010)

d.send( CMD_FILL, rgb555(r=0, g=0, b=0) )
d.send( *rect( 0, HEIGHT - 10, WIDTH, 10, rgb555(0,0,8), OP_OR) )
d.send( *rect( WIDTH - 10, 0, 10, HEIGHT, rgb555(0,0,8), OP_OR) )
d.send( *rect( 50,  150, 200, 60, rgb555(0,0,8), OP_OR) )
d.send( *rect( 150, 140, 50, 100, rgb555(0,8,0), OP_OR) )
sleep(0.1)

#####################################################################

import Image
import ImageFont
import ImageDraw

fontsize = 18
font = ImageFont.truetype('couri.ttf', fontsize)
image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
draw = ImageDraw.Draw(image)

txt = [
    u'RaspberryPi USB display',
    u'python + libusb',
    u'(320x240)',
    u'github.com/leakim/...',
]
for i, line in enumerate( txt ):
    draw.text((0, i*fontsize), line, (31,31,31), font=font)
img = Img(WIDTH, HEIGHT)
for i, p in enumerate(image.getdata()):
    img.pset(i, *p)
d.send( *img.pack(0, 0, OP_OR) )

#####################################################################

d.close()
