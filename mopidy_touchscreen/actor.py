import logging
import os
import re
import traceback
from threading import Thread
from collections import deque
from enum import Enum, auto

import pygame
import pykka
from mopidy import core, exceptions

from .screen_manager import ScreenManager, Screen, ScreenNames

logger = logging.getLogger(__name__)

class MPDEventType(Enum):
    Track_Playback_Started = auto()
    Track_Playback_Ended = auto()
    Playback_State_Changed = auto()
    Volume_Changed = auto()
    Tracklist_Changed = auto()
    Options_Changed = auto()
    Playlists_Loaded = auto()
    Stream_Title_Changed = auto()

class MPDEvent:
    def __init__(self, evtype, data):
        self.evtype = evtype
        self.data = data
    def __str__(self):
        return 'MPDEvent({}, {})'.format(self.evtype.name, self.data)

class TouchScreen(pykka.ThreadingActor, core.CoreListener):
    def __init__(self, config, core):
        super(TouchScreen, self).__init__()
        logger.info("Instantiated TouchScreen")
        self.core = core
        self.running = False
        self.screen = None
        self.screen_manager = None

        cfg = config['touchscreen']
        self.cursor = cfg.get('cursor')
        self.cache_dir = cfg.get('cache_dir')
        self.fullscreen = cfg.get('fullscreen')
        self.screen_size = (cfg.get('screen_width'), cfg.get('screen_height'))
        self.resolution_factor = cfg.get('resolution_factor')

        self.start_screen = ScreenNames.get(cfg.get('start_screen'))
        if self.start_screen is None:
            self.start_screen = Screen.Index

        # None means: do not switch screens after inactivity
        self.main_screen = ScreenNames.get(cfg.get('main_screen'))
        self.inactivity_timeout = 20  # seconds

        if cfg.get('sdl_videodriver') != "none":
            os.environ["SDL_VIDEODRIVER"] = cfg.get('sdl_videodriver')
        if cfg.get('sdl_video_render_driver') != "none":
            os.environ["SDL_RENDER_DRIVER"] = cfg.get('sdl_video_render_driver')
        if cfg.get('sdl_mousedriver').lower() != "none":
            os.environ["SDL_MOUSEDRV"] = cfg.get('sdl_mousedriver')
        if cfg.get('sdl_mousedev').lower != "none":
            os.environ["SDL_MOUSEDEV"] = cfg.get('sdl_mousedev')
        if cfg.get('sdl_audiodriver').lower != "none":
            os.environ["SDL_AUDIODRIVER"] = cfg.get('sdl_audiodriver')
        os.environ["SDL_PATH_DSP"] = cfg.get('sdl_path_dsp')

        video_device_idx = cfg.get('sdl_video_device_index')
        if  video_device_idx == "none":
            video_device = cfg.get("sdl_video_device")
            vd_link = ""
            if video_device != "none":
                try:
                    vd_link = os.readlink("/dev/dri/by-path/"+video_device)
                    match = re.search(r'card([0-9]*)$', vd_link)
                    if match is None:
                        raise ValueError
                    idx = match.group(1)
                    if idx == "":
                        raise ValueError
                    video_device_idx = idx
                except FileNotFoundError:
                    logger.error("sdl_video_device '{}' does not exist".format(video_device))
                except ValueError:
                    logger.error("sdl_video_device '{}' points to invalid node name '{}'".format(video_device, vd_link))

            if video_device_idx != "none":
                logger.info('Setting SDL_VIDEO_DEVICE_INDEX to {}'.format(video_device_idx))
                os.environ["SDL_VIDEO_DEVICE_INDEX"] = video_device_idx

    def get_display_surface(self, size):
        logger.info("getting display surface of size {}".format(size))
        try:
            flags = 0 # pygame.OPENGL
            if self.fullscreen:
                flags |= pygame.FULLSCREEN
            else:
                flags |= pygame.RESIZABLE
            self.screen = pygame.display.set_mode(size, flags | pygame.FULLSCREEN)
        except Exception:
            raise exceptions.FrontendError("Error on display init:\n" + traceback.format_exc())

    def start_thread(self):
        pygame.init()
        pygame.display.set_caption("Mopidy-Touchscreen")
        self.get_display_surface(self.screen_size)
        pygame.mouse.set_visible(self.cursor)

        self.screen_manager = ScreenManager(self.screen_size, self.core, self.cache_dir, self.resolution_factor,
                                            self.start_screen, self.main_screen)

        self.screen_manager.set_inactivity_timeout(self.inactivity_timeout)

        logger.info("starting event handling loop")
        clock = pygame.time.Clock()
        pygame.event.set_blocked(pygame.MOUSEMOTION)
        while self.running:
            clock.tick(12)

            while len(self.mpdqueue) > 0:
                mpd_ev = self.mpdqueue.popleft()
                logger.debug(f'mpd_ev={mpd_ev}')
                try:
                    if mpd_ev.evtype == MPDEventType.Track_Playback_Started:
                        self.screen_manager.track_started(mpd_ev.data)
                    elif mpd_ev.evtype == MPDEventType.Track_Playback_Ended:
                        self.screen_manager.track_playback_ended(mpd_ev.data["tl_track"], mpd_ev.data["time_position"])
                    elif mpd_ev.evtype == MPDEventType.Volume_Changed:
                        self.screen_manager.volume_changed(mpd_ev.data)
                    elif mpd_ev.evtype == MPDEventType.Playback_State_Changed:
                        self.screen_manager.playback_state_changed(mpd_ev.data["old_state"], mpd_ev.data["new_state"])
                    elif mpd_ev.evtype == MPDEventType.Tracklist_Changed:
                        self.screen_manager.tracklist_changed()
                    elif mpd_ev.evtype == MPDEventType.Options_Changed:
                        self.screen_manager.options_changed()
                    elif mpd_ev.evtype == MPDEventType.Playlists_Loaded:
                        self.screen_manager.playlists_loaded()
                    elif mpd_ev.evtype == MPDEventType.Stream_Title_Changed:
                        self.screen_manager.stream_title_changed(mpd_ev.data)
                except:
                    traceback.print_exc()

            if self.screen is not None:
                self.screen_manager.update(self.screen)

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
            self.mpdqueue = deque()
            self.running = True
            thread = Thread(target=self.start_thread, name="Pygame UI")
            thread.start()
        except:
            traceback.print_exc()

    def on_stop(self):
        self.running = False

    def track_playback_started(self, tl_track):
        self.mpdqueue.append(MPDEvent(MPDEventType.Track_Playback_Started, tl_track))

    def track_playback_ended(self, tl_track, time_position):
        self.mpdqueue.append(MPDEvent(MPDEventType.Track_Playback_Ended,
                                      {"tl_track": tl_track, "time_position": time_position}))

    def volume_changed(self, volume):
        self.mpdqueue.append(MPDEvent(MPDEventType.Volume_Changed, volume))

    def playback_state_changed(self, old_state, new_state):
        self.mpdqueue.append(MPDEvent(MPDEventType.Playback_State_Changed,
                                      {"old_state": old_state, "new_state": new_state}))

    def tracklist_changed(self):
        self.mpdqueue.append(MPDEvent(MPDEventType.Tracklist_Changed, None))

    def options_changed(self):
        self.mpdqueue.append(MPDEvent(MPDEventType.Options_Changed, None))

    def playlists_loaded(self):
        self.mpdqueue.append(MPDEvent(MPDEventType.Playlists_Loaded, None))

    def stream_title_changed(self, title):
        self.mpdqueue.append(MPDEvent(MPDEventType.Stream_Title_Changed, title))
