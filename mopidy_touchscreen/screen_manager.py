import logging
import os
import traceback
from enum import Enum

import mopidy.core
import pygame
from pkg_resources import Requirement, resource_filename

from .graphic_utils import DynamicBackground, \
    ScreenObjectsManager, TouchAndTextItem
from .input_manager import InputManager
from .screens import BaseScreen, Keyboard, LibraryScreen, MainScreen, \
    MenuScreen, PlaylistScreen, SearchScreen, Tracklist

logger = logging.getLogger(__name__)

Screen = Enum('Screen', 'Search Player Tracklist Library Playlists Menu')
ScreenNames = {
    'search': Screen.Search,
    'player': Screen.Player,
    'tracklist': Screen.Tracklist,
    'library': Screen.Library,
    'playlists': Screen.Playlists,
    'menu': Screen.Menu,
}


class ScreenManager:
    def __init__(self, size, core, cache, resolution_factor, start_screen=Screen.Library, main_screen=None):
        self.core = core
        self.cache = cache
        self.fonts = {}
        self.background = None
        self.current_screen = start_screen
        self.main_screen = main_screen

        # Init variables in init
        self.base_size = None
        self.size = None
        self.screens = None
        # avoid cyclic import of this package from screens.py
        self.screen_type = Screen
        self.track = None
        self.input_manager = InputManager(size)
        self.down_bar_objects = ScreenObjectsManager()
        self.down_bar = None
        self.keyboard = None
        self.update_type = BaseScreen.update_all

        self.inactivity_timer_count = 0
        self.inactivity_timer = 0
        self.frame_count = 0

        self.resolution_factor = resolution_factor

        self.init_manager(size)

        self.last_surface = pygame.Surface(size)

    def init_manager(self, size):
        self.size = size
        self.base_size = self.size[1] / self.resolution_factor

        self.background = DynamicBackground(self.size)
        font_icon = resource_filename(
            Requirement.parse("mopidy-touchscreen"),
            "mopidy_touchscreen/icomoon.ttf")

        font_base = resource_filename(
            Requirement.parse("mopidy-touchscreen"),
            "mopidy_touchscreen/NotoSans-Regular.ttf")
        self.fonts['base'] = pygame.font.Font(font_base, int(self.base_size * 0.9))
        self.fonts['icon'] = pygame.font.Font(font_icon, int(self.base_size * 0.9))

        self.track = None

        # Menu buttons

        button_size = (self.size[0] / 6, self.base_size)

        menu_icons = [u" \ue986", u" \ue600", u"\ue60d", u" \ue604", u" \ue605", u" \ue60a"]

        x = 0
        i = 0
        while i < 6:
            button = TouchAndTextItem(self.fonts['icon'], menu_icons[i],
                                      (x, self.size[1] - self.base_size),
                                      button_size, center=True)
            self.down_bar_objects.set_touch_object("menu_" + Screen(i + 1).name, button)
            x = button.get_right_pos()
            i += 1
            button.pos = (button.pos[0], self.size[1] - button.rect_in_pos.size[1])

        # Down bar
        self.down_bar = pygame.Surface(
            (self.size[0], button.rect_in_pos.size[1]),
            pygame.SRCALPHA)
        self.down_bar.fill((0, 0, 0, 200))

        screen_size = (size[0], self.size[1] - button.rect.size[1])

        try:
            self.screens = {
                Screen.Search: SearchScreen(screen_size, self.base_size, self, self.fonts),
                Screen.Player: MainScreen(screen_size, self.base_size, self, self.fonts,
                                          self.cache, self.core, self.background),
                Screen.Tracklist: Tracklist(screen_size, self.base_size, self, self.fonts),
                Screen.Library: LibraryScreen(screen_size, self.base_size, self, self.fonts),
                Screen.Playlists: PlaylistScreen(screen_size,
                                                 self.base_size, self, self.fonts),
                Screen.Menu: MenuScreen(screen_size, self.base_size, self, self.fonts, self.core)
            }
        except:
            traceback.print_exc()

        self.options_changed()
        self.mute_changed(self.core.mixer.get_mute().get())
        playback_state = self.core.playback.get_state().get()
        self.playback_state_changed(playback_state,
                                    playback_state)
        self.screens[Screen.Menu].check_connection()

        self.change_screen(self.current_screen)

        self.update_type = BaseScreen.update_all

    def get_update_type(self):
        if self.update_type == BaseScreen.update_all:
            self.update_type = BaseScreen.no_update
            return BaseScreen.update_all
        else:
            if self.keyboard:
                return BaseScreen.no_update
            else:
                if self.background.should_update():
                    return BaseScreen.update_all
                else:
                    if self.screens[self.current_screen].should_update():
                        return BaseScreen.update_partial
                    else:
                        return BaseScreen.no_update

    def set_inactivity_timeout(self, timeout):
        self.inactivity_timer = timeout

    def reset_inactivity_timer(self):
        self.inactivity_timer_count = self.inactivity_timer

    def inactivity_timeout(self):
        if self.inactivity_timer_count <= 0:
            return False

        if self.frame_count <= 0:
            self.frame_count = 12

        self.frame_count -= 1
        if self.frame_count > 0:
            return False

        self.inactivity_timer_count -= 1
        if self.inactivity_timer_count > 0:
            return False

        return True

    def update(self, screen):
        if self.main_screen is not None and \
                self.current_screen != self.main_screen and \
                self.inactivity_timeout():
            self.change_screen(self.main_screen)

        update_type = self.get_update_type()
        if update_type != BaseScreen.no_update:
            rects = []
            if update_type == BaseScreen.update_partial:
                surface = self.last_surface
                self.screens[self.current_screen].find_update_rects(rects)
                self.background.draw_background_in_rects(surface, rects)
            else:
                surface = self.background.draw_background()

            if self.keyboard:
                self.keyboard.update(surface, update_type, rects)
            else:
                self.screens[self.current_screen]. \
                    update(surface, update_type, rects)
                surface.blit(self.down_bar, (0, self.size[1] - self.down_bar.get_size()[1]))
                self.down_bar_objects.render(surface)

            if update_type == BaseScreen.update_all:
                screen.blit(surface, (0, 0))
                pygame.display.flip()
            else:
                for rect in rects:
                    screen.blit(surface, rect, area=rect)
                    pygame.display.update(rects)
            self.last_surface = surface

    def track_started(self, track):
        self.track = track
        self.screens[Screen.Player].track_started(track.track)
        self.screens[Screen.Tracklist].track_started(track)

    def track_playback_ended(self, tl_track, time_position):
        self.screens[Screen.Player].track_playback_ended(tl_track, time_position)

    def event(self, event):
        event = self.input_manager.event(event)
        if event is not None:
            self.reset_inactivity_timer()
            if self.keyboard is not None:
                self.keyboard.touch_event(event)
            elif not self.manage_event(event):
                self.screens[self.current_screen].touch_event(event)
            self.update_type = BaseScreen.update_all

    def manage_event(self, event):
        if event.type == InputManager.click:
            objects = \
                self.down_bar_objects.get_touch_objects_in_pos(
                    event.current_pos)
            return self.click_on_objects(objects, event)
        else:
            if event.type == InputManager.key and not event.longpress:
                direction = event.direction
                if direction == InputManager.right or direction == InputManager.left:
                    if not self.screens[self.current_screen].change_screen(direction):
                        cur = self.current_screen.value
                        if direction == InputManager.right:
                            cur += 1
                        else:
                            cur -= 1
                        try:
                            self.change_screen(Screen(cur))
                        except:
                            pass
                    return True
                elif isinstance(event.unicode, str):
                    if event.unicode == "n":
                        self.core.playback.next()
                    elif event.unicode == "p":
                        self.core.playback.previous()
                    elif event.unicode == "+":
                        volume = self.core.mixer.get_volume().get() + 10
                        if volume > 100:
                            volume = 100
                        self.core.mixer.set_volume(volume)
                    elif event.unicode == "-":
                        volume = self.core.mixer.get_volume().get() - 10
                        if volume < 0:
                            volume = 0
                        self.core.mixer.set_volume(volume)
                    elif event.unicode == " ":
                        playstate = self.core.playback.get_state().get()
                        if playstate == mopidy.core.PlaybackState.PLAYING:
                            self.core.playback.pause()
                        elif playstate == mopidy.core.PlaybackState.PAUSED:
                            self.core.playback.resume()
                        else:
                            self.core.playback.play()
                    elif event.unicode == "x":
                        self.core.playback.stop()
                    elif event.unicode == "m":
                        mute = not self.core.mixer.get_mute().get()
                        self.core.mixer.set_mute(mute)
                        self.mute_changed(mute)
                    elif event.unicode == 's':
                        shuffle = not self.core.tracklist.get_random().get()
                        self.core.tracklist.set_random(shuffle)
                    elif event.unicode == 'r':
                        repeat = not self.core.tracklist.get_repeat().get()
                        self.core.tracklist.set_repeat(repeat)
                    elif event.unicode == 'o':
                        single = not self.core.tracklist.get_single().get()
                        self.core.tracklist.set_single(single)
                    elif event.unicode == 'q':
                        if os.system("gksu -- shutdown now -h") != 0:
                            os.system("sudo shutdown now -h")
                    elif "1" <= event.unicode <= str(len(Screen)):
                        self.change_screen(Screen(int(event.unicode)))

            return False

    def volume_changed(self, volume):
        self.screens[Screen.Player].volume_changed(volume)
        self.update_type = BaseScreen.update_all

    def playback_state_changed(self, old_state, new_state):
        self.screens[Screen.Player].playback_state_changed(
            old_state, new_state)
        self.update_type = BaseScreen.update_all

    def mute_changed(self, mute):
        self.screens[Screen.Player].mute_changed(mute)
        self.update_type = BaseScreen.update_all

    def tracklist_changed(self):
        self.screens[Screen.Tracklist].tracklist_changed()
        self.update_type = BaseScreen.update_all

    def options_changed(self):
        self.screens[Screen.Menu].options_changed()
        self.update_type = BaseScreen.update_all

    def change_screen(self, new_screen):
        logger.info(f'switching to screen "{new_screen.name}"')
        self.down_bar_objects.get_touch_object('menu_' + self.current_screen.name).set_active(False)
        self.down_bar_objects.get_touch_object('menu_' + new_screen.name).set_active(True)
        self.current_screen = new_screen
        self.update_type = BaseScreen.update_all

    def click_on_objects(self, objects, event):
        if objects is not None:
            for key in objects:
                if key.startswith('menu_'):
                    try:
                        self.change_screen(Screen[key[5:]])
                        return True
                    except:
                        logger.error(f'unknown screen "{key[5:]}"')
                        return False
        return False

    def playlists_loaded(self):
        self.screens[Screen.Playlists].playlists_loaded()
        self.update_type = BaseScreen.update_all

    def search(self, query, mode):
        self.screens[Screen.Search].search(query, mode)
        self.update_type = BaseScreen.update_all

    def resize(self, event):
        self.init_manager(event.size)
        self.update_type = BaseScreen.update_all

    def stream_title_changed(self, title):
        self.screens[Screen.Player].stream_title_changed(title)
        self.update_type = BaseScreen.update_all

    def open_keyboard(self, input_listener):
        self.keyboard = Keyboard(self.size, self.base_size, self,
                                 self.fonts, input_listener)
        self.update_type = BaseScreen.update_all

    def close_keyboard(self):
        self.keyboard = None
        self.update_type = BaseScreen.update_all
