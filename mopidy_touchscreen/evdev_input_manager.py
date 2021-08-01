import logging

import evdev
from evdev import ecodes as ec
import selectors
import pygame
import threading

logger = logging.getLogger(__name__)


class EvDevManager:
    keycodes = {
        ec.KEY_LEFT: (pygame.K_LEFT, None),
        ec.KEY_RIGHT: (pygame.K_RIGHT, None),
        ec.KEY_UP: (pygame.K_UP, None),
        ec.KEY_DOWN: (pygame.K_DOWN, None),
        ec.KEY_SPACE: (pygame.K_RETURN, None),
        ec.KEY_ENTER: (pygame.K_RETURN, None),
        ec.KEY_OK: (pygame.K_RETURN, None),
        ec.KEY_VOLUMEDOWN: (pygame.K_MINUS, '-'),
        ec.KEY_VOLUMEUP: (pygame.K_PLUS, '+'),
        ec.KEY_1: (pygame.K_1, '1'),
        ec.KEY_2: (pygame.K_2, '2'),
        ec.KEY_3: (pygame.K_3, '3'),
        ec.KEY_4: (pygame.K_4, '4'),
        ec.KEY_5: (pygame.K_5, '5'),
        ec.KEY_6: (pygame.K_6, '6'),
        ec.KEY_PREVIOUS: (pygame.K_PAGEUP, 'p'),
        ec.KEY_NEXT: (pygame.K_PAGEDOWN, 'n'),
        ec.KEY_PLAYPAUSE: (pygame.K_PAUSE, ' '),
        ec.KEY_STOP: (pygame.K_x, 'x'),
        ec.KEY_AGAIN: (pygame.K_r, 'r'),
        ec.KEY_SHUFFLE: (pygame.K_s, 's'),
        ec.KEY_MUTE: (pygame.K_m, 'm'),
        ec.KEY_AB: (pygame.K_o, 'o'),  # single track mode
        ec.KEY_POWER: (pygame.K_POWER, 'q'),
    }

    def __init__(self):
        self.killswitch = False
        self.thread = None
        self.button_devices = []
        self.get_devices()

    def get_devices(self):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            if device.name.startswith("lircd-uinput"):
                # grab all lircd uinput devices
                device.grab()
                self.button_devices.append(device)
            elif device.phys.startswith("gpio-keys"):
                # only grab GPIO keys we're actually using
                cap = device.capabilities()
                codes = cap.get(1)
                if codes is None or not isinstance(codes, list) or len(codes) < 1:
                    continue
                if codes[0] not in self.keycodes:
                    continue
                device.grab()
                self.button_devices.append(device)

    def handle_event(self, event):
        if event.type is evdev.ecodes.EV_KEY and event.code in self.keycodes:
            pyg_attr = {}
            if event.value in [evdev.events.KeyEvent.key_down, evdev.events.KeyEvent.key_hold]:
                pyg_type = pygame.KEYDOWN
                pyg_attr['unicode'] = self.keycodes[event.code][1]
            else:
                pyg_type = pygame.KEYUP

            pyg_attr['key'] = self.keycodes[event.code][0]

            # print(pyg_attr, pyg_type)
            ev = pygame.event.Event(pyg_type, pyg_attr)
            pygame.event.post(ev)

    def event_loop(self):
        selector = selectors.DefaultSelector()
        for device in self.button_devices:
            selector.register(device, selectors.EVENT_READ)

        while True:
            if self.killswitch:
                for device in self.button_devices:
                    device.ungrab()
                return

            for key, mask in selector.select(timeout=1):
                device = key.fileobj
                for event in device.read():
                    self.handle_event(event)

    def run(self):
        self.killswitch = False
        self.thread = threading.Thread(target=self.event_loop)
        self.thread.start()

    def stop(self):
        self.killswitch = True
