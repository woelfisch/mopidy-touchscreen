import logging
import os
import traceback
from threading import Thread
import syslog

from mopidy import core, exceptions

import pygame

import pykka

from .screen_manager import ScreenManager, Screen, ScreenNames


logger = logging.getLogger(__name__)

class TouchScreen(pykka.ThreadingActor, core.CoreListener):
    def __init__(self, config, core):
        super(TouchScreen, self).__init__()
        logger.info("Instantiated TouchScreen")
        self.core = core
        self.running = False

        cfg = config['touchscreen']
        self.cursor = cfg.get('cursor')
        self.cache_dir = cfg.get('cache_dir')
        self.fullscreen = cfg.get('fullscreen')
        self.screen_size = (cfg.get('screen_width'), cfg.get('screen_height'))
        self.resolution_factor = cfg.get('resolution_factor')
        self.fbdev = cfg.get('fbdev')
        self.sdl_output = cfg.get('sdl_output')

        self.start_screen = ScreenNames.get(cfg.get('start_screen'))
        if self.start_screen is None:
            self.start_screen = Screen.Index

        # None means: do not switch screens after inactivity
        self.main_screen = ScreenNames.get(cfg.get('main_screen'))
        self.inactivity_timeout = 20    # seconds

        if self.fbdev.lower() != "none":
            os.environ["SDL_FBDEV"] = self.fbdev
        if cfg.get('sdl_videodriver') != "none":
            os.environ["SDL_VIDEODRIVER"] = cfg.get('sdl_videodriver')
        if cfg.get('sdl_mousedriver').lower() != "none":
            os.environ["SDL_MOUSEDRV"] = cfg.get('sdl_mousedriver')
        if cfg.get('sdl_mousedev').lower != "none":
            os.environ["SDL_MOUSEDEV"] = cfg.get('sdl_mousedev')
        if cfg.get('sdl_audiodriver').lower != "none":
            os.environ["SDL_AUDIODRIVER"] = cfg.get('sdl_audiodriver')
        os.environ["SDL_PATH_DSP"] = cfg.get('sdl_path_dsp')

        pygame.init()
        pygame.display.set_caption("Mopidy-Touchscreen")
        self.get_display_surface(self.screen_size)
        pygame.mouse.set_visible(self.cursor)
        self.screen_manager = ScreenManager(self.screen_size,
                                            self.core,
                                            self.cache_dir,
                                            self.resolution_factor,
                                            self.start_screen,
                                            self.main_screen)

        self.screen_manager.set_inactivity_timeout(self.inactivity_timeout)

        self.evdev = cfg.get('evdev')
        if self.evdev:
            from .evdev_input_manager import EvDevManager
            self.evdev_manager = EvDevManager()
            self.evdev_manager.run()


    # https://stackoverflow.com/questions/54778105/python-pygame-fails-to-output-to-dev-fb1-on-a-raspberry-pi-tft-screen
    # We have to initialize SDL in any case — otherwise Surface.convert*() will fail, 
    # since those functions check SDL_WasInit() in C code. This means no monkey 
    # patching either. Hence, SDL will always grab the accalerated framebuffer (ie,
    # RPi's HDMI output) and you can't really do anything usuful with it, and I
    # don't know what happens if no monitor is attached to it...

    def get_display_surface(self, size):
        try:
            if self.fullscreen:
                self.display = pygame.display.set_mode(size, pygame.FULLSCREEN)
            else:
                self.display = pygame.display.set_mode(size, pygame.RESIZABLE)
        except Exception:
            raise exceptions.FrontendError("Error on display init:\n" + traceback.format_exc())

        if self.sdl_output:
            self.screen = self.display
        else:
            self.screen = pygame.Surface(size)

    def refresh_display(self):
        with open(self.fbdev,'wb') as f:
            f.write(self.screen.convert(16,0).get_buffer())

    def start_thread(self):
        clock = pygame.time.Clock()
        pygame.event.set_blocked(pygame.MOUSEMOTION)
        while self.running:
            clock.tick(12)

            self.screen_manager.update(self.screen)
            if not self.sdl_output:
                self.refresh_display()

            for event in pygame.event.get():
                # logger.info(f"got event {event}")
                if event.type == pygame.QUIT:
                    os.system("pkill mopidy")
                elif event.type == pygame.VIDEORESIZE:
                    self.get_display_surface(event.size)
                    self.screen_manager.resize(event)
                else:
                    self.screen_manager.event(event)
        pygame.quit()

    def on_start(self):
        logger.info("Attempting to start TouchScreen")
        try:
            self.running = True
            thread = Thread(target=self.start_thread)
            thread.start()
        except:
            traceback.print_exc()

    def on_stop(self):
        self.running = False

    def track_playback_started(self, tl_track):
        try:
            logger.info(f'track_playback_started({tl_track})')
            self.screen_manager.track_started(tl_track)
        except:
            traceback.print_exc()

    def volume_changed(self, volume):
        self.screen_manager.volume_changed(volume)

    def playback_state_changed(self, old_state, new_state):
        self.screen_manager.playback_state_changed(old_state,
                                                   new_state)

    def tracklist_changed(self):
        try:
            self.screen_manager.tracklist_changed()
        except:
            traceback.print_exc()

    def track_playback_ended(self, tl_track, time_position):
        self.screen_manager.track_playback_ended(tl_track,
                                                 time_position)

    def options_changed(self):
        try:
            self.screen_manager.options_changed()
        except:
            traceback.print_exc()

    def playlists_loaded(self):
        self.screen_manager.playlists_loaded()

    def stream_title_changed(self, title):
        self.screen_manager.stream_title_changed(title)
