# SPDX-FileCopyrightText: 2024 M5Stack Technology CO LTD
# Modified by k98kurz 2024
#
# SPDX-License-Identifier: MIT

# StampPico startup script
import M5
import time
import network
import machine
import binascii
import os
from . import Startup
from hardware import RGB


main_code = '''
from asyncio import sleep_ms, run, gather
from collections import deque
from machine import Pin
from micropycelium import Packager, debug, ESPNowInterface, Beacon
from neopixel import NeoPixel

def write_file(fname: str, data: str):
    with open(f'/{fname}', 'w') as f:
        f.write(data)

def read_file(fname: str) -> str:
    with open(f'/{fname}', 'r') as f:
        return f.read()

# RGB LED of the M5stamp-Pico
rgb = NeoPixel(Pin(27, Pin.OUT), 1)
rq = deque([], 10)
async def rloop():
    while True:
        r = rq.popleft() if len(rq) else (0, 0, 0)
        rgb.fill(r)
        rgb.write()
        await sleep_ms(100 if any(r) else 1)

# Button of the M5stamp-Pico
btn = Pin(39, Pin.IN)
btnq = deque([], 5)

# monitor a button on a specific pin
async def monitor_btn(p: Pin, q: deque, debounce_ms: int):
    while True:
        if not p.value():
            q.appendleft(1)
            Beacon.invoke('start')
            await sleep_ms(debounce_ms)
        await sleep_ms(1)

# useful for blinking LEDs on a breadboard
async def blink(p: Pin, ms: int):
    v = p.value()
    p.value(not v)
    await sleep_ms(ms)
    p.value(v)
async def bloop(q: deque, p: Pin):
    while True:
        while len(q):
            q.popleft()
            await blink(p, 100)
        await sleep_ms(1)

# add some hooks
def recv_hook(*args, **kwargs):
    debug('Beacon.receive')
    rq.append((0, 0, 255))
def brdcst_hook(*args, **kwargs):
    debug('Beacon.broadcast')
    rq.append((255, 0, 0))
def send_hook(*args, **kwargs):
    debug('Beacon.send')
    rq.append((126, 126, 126))

Beacon.add_hook('receive', recv_hook)
Beacon.add_hook('broadcast', brdcst_hook)
Beacon.add_hook('send', send_hook)

def debug_name(name: str):
    def inner(*args):
        debug(name)
    return inner

ESPNowInterface.add_hook('process:receive', debug_name(f'Interface({ESPNowInterface.name}).process:receive'))
ESPNowInterface.add_hook('process:send', debug_name(f'Interface({ESPNowInterface.name}).process:send'))
ESPNowInterface.add_hook('process:broadcast', debug_name(f'Interface({ESPNowInterface.name}).process:broadcast'))
Packager.add_hook('send', debug_name('Packager.send'))
Packager.add_hook('broadcast', debug_name('Packager.broadcast'))
Packager.add_hook('receive', debug_name('Packager.receive'))
Packager.add_hook('rns', debug_name('Packager.rns'))
Packager.add_hook('send_packet', debug_name('Packager.send_packet'))
Packager.add_hook('_send_datagram', debug_name('Packager._send_datagram'))
Packager.add_hook('deliver', debug_name('Packager.deliver'))
Packager.add_hook('add_peer', debug_name('Packager.add_peer'))
Packager.add_hook('remove_peer', debug_name('Packager.remove_peer'))

Beacon.invoke('start')

def start():
    run(gather(Packager.work(), monitor_btn(btn, btnq, 800), rloop()))

start()
'''



# StampPico startup menu
class StampPico_Startup(Startup):
    COLOR_RED = 0xFF0000  # WiFi not connected
    COLOR_BLUE = 0x0000FF  # WiFi connected, server not connected
    COLOR_GREEN = 0x00FF00  # WiFi connected, server connected

    def __init__(self) -> None:
        super().__init__()
        self.rgb = RGB()
        self.rgb.set_color(0, self.COLOR_RED)
        self.rgb.set_brightness(30)

    def show_hits(self, hits: str) -> None:
        pass

    def show_msg(self, msg: str) -> None:
        pass

    def show_ssid(self, ssid: str) -> None:
        pass

    def show_mac(self) -> None:
        mac = binascii.hexlify(machine.unique_id()).decode("utf-8").upper()
        print("Mac: " + mac[0:6] + "_" + mac[6:])

    def show_error(self, ssid: str, error: str) -> None:
        print("SSID: " + ssid + "\r\nNotice: " + error)

    def startup(self, ssid: str, pswd: str, timeout: int = 60) -> None:
        self.show_mac()

        # write main.py file if it does not exist
        try:
            with open('/flash/main.py', 'r') as f:
                if len(f.read()) < 11:
                    raise BaseException()
        except BaseException:
            with open('/flash/main.py', 'w') as f:
                f.write(main_code)
            print('wrote basic micropycelium main.py file')

        if ssid != '' and super().connect_network(ssid=ssid, pswd=pswd):
            print("Connecting to " + ssid + " ", end="")
            status = super().connect_status()
            self.rgb.set_brightness(60)
            start = time.time()
            while status is not network.STAT_GOT_IP:
                time.sleep_ms(300)
                if status is network.STAT_NO_AP_FOUND:
                    self.show_error(ssid, "NO AP FOUND")
                    break
                elif status is network.STAT_WRONG_PASSWORD:
                    self.show_error(ssid, "WRONG PASSWORD")
                    break
                elif status is network.STAT_HANDSHAKE_TIMEOUT:
                    self.show_error(ssid, "HANDSHAKE ERR")
                    break
                elif status is network.STAT_CONNECTING:
                    print(".", end="")
                status = super().connect_status()
                # connect to network timeout
                if (time.time() - start) > timeout:
                    self.show_error(ssid, "TIMEOUT")
                    break

            print(" ")
            if status is network.STAT_GOT_IP:
                print("Local IP: " + super().local_ip())
                self.rgb.set_color(0, self.COLOR_GREEN)
                self.rgb.set_brightness(100)
        else:
            self.rgb.set_color(0, self.COLOR_RED)
            self.rgb.set_brightness(100)
            self.show_error("WiFi SSID not specified", "Use M5Burner setup if you want to connect to WiFi")

