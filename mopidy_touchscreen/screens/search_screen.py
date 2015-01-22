import pygame

from base_screen import BaseScreen
from ..input import InputManager
from ..graphic_utils import *

mode_track_name = 0
mode_album_name = 1
mode_artist_name = 2


class SearchScreen(BaseScreen):
    def __init__(self, size, base_size, manager, fonts):
        BaseScreen.__init__(self, size, base_size, manager, fonts)
        self.list_view = ListView((0, self.base_size*2), (
            self.size[0], self.size[1] -
            3*self.base_size), self.base_size, manager.fonts['base'])
        self.results_strings = []
        self.results = []
        self.screen_objects = ScreenObjectsManager()
        self.query = ""

        # Query text
        text = TextItem(self.fonts['base'], self.query, (0, 0),
                        (self.size[0], self.base_size), center=True)
        self.screen_objects.set_object("query", text)

        # Mode buttons
        button_size = (self.size[0] / 3, self.base_size)
        self.mode_objects_keys = ["mode_track", "mode_album",
                                  "mode_artist"]

        # Track button
        button = TouchAndTextItem(self.fonts['base'], "Track",
                                  (0, self.base_size),
                                  button_size, center=True)
        self.screen_objects.set_touch_object(
            self.mode_objects_keys[0], button)

        # Album button
        button = TouchAndTextItem(self.fonts['base'], "Album",
                                  (button_size[0], self.base_size),
                                  button_size, center=True)
        self.screen_objects.set_touch_object(
            self.mode_objects_keys[1], button)

        # Artist button
        button = TouchAndTextItem(self.fonts['base'], "Artist",
                                  (button_size[0]*2, self.base_size),
                                  button_size, center=True)
        self.screen_objects.set_touch_object(
            self.mode_objects_keys[2], button)

        # Top Bar
        self.top_bar = pygame.Surface(
            (self.size[0], self.base_size * 2),
            pygame.SRCALPHA)
        self.top_bar.fill((0, 0, 0, 128))

        self.mode = -100
        self.set_mode(mode=mode_track_name)
        self.set_query("")

    def update(self, screen):
        screen.blit(self.top_bar, (0, 0))
        self.screen_objects.render(screen)
        self.list_view.render(screen)

    def set_mode(self, mode=mode_track_name):
        if mode is not self.mode:
            self.mode = mode
            for key in self.mode_objects_keys:
                self.screen_objects.get_touch_object(key).\
                    set_active(False)
            self.screen_objects.get_touch_object(
                self.mode_objects_keys[self.mode]).set_active(True)

    def set_query(self, query=""):
        self.query = query
        self.screen_objects.get_object("query").set_text(
            self.query, False)

    def search(self, query=None, mode=None):
        if query is not None:
            self.set_query(query)
        if mode is not None:
            self.set_mode(mode)
        if self.mode == mode_track_name:
            search_query = {'any': [self.query]}
        elif self.mode == mode_album_name:
            search_query = {'album': [self.query]}
        else:
            search_query = {'artist': [self.query]}
        if len(self.query) > 0:
            current_results = self.manager.core.library.search(
                search_query).get()
            self.results = []
            self.results_strings = []
            for backend in current_results:
                if mode == mode_track_name:
                    iterable = backend.tracks
                elif mode == mode_album_name:
                    iterable = backend.albums
                else:
                    iterable = backend.artists

                for result in iterable:
                    self.results.append(result)
                    self.results_strings.append(result.name)
            self.list_view.set_list(self.results_strings)

    def touch_event(self, touch_event):
        if touch_event.type == InputManager.click:
            clicked = self.list_view.touch_event(touch_event)
            if clicked is not None:
                self.manager.core.tracklist.clear()
                self.manager.core.tracklist.add(
                    uri=self.results[clicked].uri)
                self.manager.core.playback.play()
            else:
                clicked = self.screen_objects.get_touch_objects_in_pos(
                    touch_event.down_pos)
                if len(clicked) > 0:
                    clicked = clicked[0]
                    if clicked == self.mode_objects_keys[0]:
                        self.search(mode=0)
                    if clicked == self.mode_objects_keys[1]:
                        self.search(mode=1)
                    if clicked == self.mode_objects_keys[2]:
                        self.search(mode=2)
        else:
            self.list_view.touch_event(touch_event)