#! /usr/bin/python3

#! /usr/bin/python

import os
import time
import socket
import pigpio
from evdev import InputDevice, ecodes, list_devices, categorize

DEBUG = True

brightness = None
disable = False

class PWM:
  BRIGHTNESS_FILE = "/var/local/remote-daemon/brightness"
  BRIGHTNESS_MAX = 255
  BRIGHTNESS_DEFAULT = 96
  BRIGHTNESS_GPIO = 18

  def __init__(self, gpio=None):
    self.pi = pigpio.pi()

    if gpio is None:
      self.gpio = self.BRIGHTNESS_GPIO
    else:
      self.gpio = gpio

    self.brightness = self.BRIGHTNESS_DEFAULT

  def update(self, increment=None, value=None):
    if self.brightness is None and value is None:
        try:
            with open(self.BRIGHTNESS_FILE, "r") as fp:
                self.brightness = int(fp.read())
        except:
            self.brightness = self.BRIGHTNESS_DEFAULT

    if value is not None:
        self.brightness = value
    elif increment is not None:
        self.brightness += increment

    self.brightness = max(self.brightness, 0)
    self.brightness = min(self.brightness, self.BRIGHTNESS_MAX)

    if DEBUG:
        print(f"brightness={self.brightness}")

    self.pi.set_PWM_dutycycle(self.gpio, self.brightness)

    with open(self.BRIGHTNESS_FILE, "w+") as fp:
        fp.write(str(self.brightness))

  def up(self):
    self.update(increment=16)

  def down(self):
    self.update(increment=-16)

class EventHandler():
  DEVICE_NAME = "gpio_ir_recv"

  def __init__(self, pwm):
    self.device = None
    self.disable = False
    self.pwm = pwm

    devices = [InputDevice(path) for path in list_devices()]

    while self.device is None:
      for device in devices:
        if device.name == self.DEVICE_NAME:
          self.device = device
          break
      if self.device is None:
        time.sleep(1)

  def loop(self):
    if self.device is None:
      print("No IR device found")
      return

    for ev in self.device.read_loop():
      if self.disable: continue
      if DEBUG:
        print(categorize(ev))

      if ev.code == ecodes.KEY_BRIGHTNESSUP:
        self.pwm.up()
      elif ev.code == ecodes.KEY_BRIGHTNESSDOWN:
        self.pwm.down()

    if action == "key_brightnessup":
      pwm.up()
    elif action == "key_brightnessdown":
      pwm.down()

pwm = PWM()
pwm.update()
lirc = EventHandler(pwm)
lirc.loop()

