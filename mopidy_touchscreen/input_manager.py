import logging
import time

from enum import Enum
from .sdl_scancodes import *
import pygame

logger = logging.getLogger(__name__)

class InputManager:
    long_click_min_time = 0.8

    special_keys = [pygame.K_DOWN, pygame.K_UP, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN]

    # USB HID Usage Codes, see https://deskthority.net/wiki/Scancode
    # or rather SDL scancodes, see https://github.com/libsdl-org/SDL/blob/main/include/SDL_scancode.h
    rc_keys = {
        SC_POWER: 'q', SC_VOLUMEDOWN: '-', SC_VOLUMEUP: '+', SC_AUDIONEXT: 'n', SC_AUDIOPREV: 'p',
        SC_MUTE: 'm', SC_AUDIOPLAY: ' ', SC_AUDIOSTOP: 'x', SC_S: 's', SC_R: 'r',
        SC_AGAIN: 'o', SC_1: '1', SC_2: '2', SC_3: '3', SC_4: '4', SC_5: '5', SC_6: '6',
        SC_7: '7', SC_8: '8', SC_9: '9', SC_HOME: '2'
    }

    def __init__(self, size):
        self.down_pos = (0, 0)
        self.up_pos = (0, 0)
        self.screen_size = size
        self.max_move_margin = self.screen_size[1] / 6
        self.min_swipe_move = self.screen_size[1] / 3
        self.down_button = -1
        self.down_time = -1
        self.last_key = -1

    def event(self, event):
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 4:
                touch_event = InputEvent(InputEvent.action.swipe, self.down_pos, self.up_pos,
                                         True, InputEvent.course.up, None)
                return touch_event
            elif event.button == 5:
                touch_event = InputEvent(InputEvent.action.swipe, self.down_pos, self.up_pos,
                                         True, InputEvent.course.down, None)
                return touch_event
            elif event.button == 1 and self.down_button == 1:
                touch_event = self.mouse_up(event)
                return touch_event
            elif event.button == 3 and self.down_button == 3:
                touch_event = InputEvent(InputEvent.action.long_click, self.down_pos, self.up_pos, None, None, None)
                return touch_event
            else:
                return None
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.mouse_down(event)
            return None
        elif event.type == pygame.KEYDOWN:
            return self.key_down(event)
        elif event.type == pygame.KEYUP:
            return self.key_up(event)

    def key_down(self, event):
        logger.debug(f"event {event}")
        if event.scancode in InputManager.rc_keys:
            event.unicode = InputManager.rc_keys[event.scancode]
        if event.unicode is not None and len(event.unicode) > 0 and event.key not in InputManager.special_keys:
            return InputEvent(InputEvent.action.key_press, None, None, None, None, unicode=event.unicode)
        else:
            self.last_key = event.key
            self.down_time = time.time()
            return None

    def key_up(self, event):
        if self.last_key == event.key:
            if self.last_key == pygame.K_DOWN:
                direction = InputEvent.course.down
            elif self.last_key == pygame.K_UP:
                direction = InputEvent.course.up
            elif self.last_key == pygame.K_LEFT:
                direction = InputEvent.course.left
            elif self.last_key == pygame.K_RIGHT:
                direction = InputEvent.course.right
            elif self.last_key == pygame.K_RETURN:
                direction = InputEvent.course.enter
            else:
                return None
            if direction is not None:
                if time.time() - self.down_time > InputManager.long_click_min_time:
                    longpress = True
                else:
                    longpress = False
                return InputEvent(InputEvent.action.key_press, None, None, None, direction,
                                  self.last_key, longpress=longpress)

    def mouse_down(self, event):
        self.down_pos = event.pos
        self.down_button = event.button
        self.down_time = time.time()

    def mouse_up(self, event):
        self.up_pos = event.pos
        if abs(self.down_pos[0] -
                self.up_pos[0]) < self.max_move_margin:
            if abs(self.down_pos[1] -
                    self.up_pos[1]) < self.max_move_margin:
                if time.time() - InputManager.long_click_min_time > self.down_time:
                    return InputEvent(InputEvent.action.long_click, self.down_pos, self.up_pos, None, None)
                else:
                    return InputEvent(InputEvent.action.click, self.down_pos, self.up_pos, None, None)
            elif abs(self.down_pos[1] - self.up_pos[1]) > self.min_swipe_move:
                return InputEvent(InputEvent.action.swipe, self.down_pos, self.up_pos, True, None)
        elif self.down_pos[1] - self.up_pos[1] < self.max_move_margin:
            if abs(self.down_pos[0] - self.up_pos[0]) > self.min_swipe_move:
                return InputEvent(InputEvent.action.swipe, self.down_pos, self.up_pos, False, None)


class InputEvent:
    action = Enum("action", "click swipe long_click key_press")
    course = Enum("course", "down up left right enter")

    def __init__(self, event_type, down_pos, current_pos, vertical, direction, unicode=None, longpress=False):
        self.type = event_type
        self.down_pos = down_pos
        self.current_pos = current_pos
        self.unicode = unicode
        self.longpress = longpress

        if event_type is InputEvent.action.swipe and direction is None:
            if vertical:
                if self.down_pos[1] < self.current_pos[1]:
                    self.direction = InputEvent.course.down
                else:
                    self.direction = InputEvent.course.up
            else:
                if self.down_pos[0] < self.current_pos[0]:
                    self.direction = InputEvent.course.right
                else:
                    self.direction = InputEvent.course.left
        else:
            self.direction = direction
