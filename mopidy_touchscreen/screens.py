import pygame
import mopidy.core
import mopidy.models
import hashlib
import logging
import os
import traceback
import time
import urllib.request
import urllib.parse
from threading import Thread
from enum import Enum
import socket
from mopidy.models import Track

from .graphic_utils import Progressbar, ScreenObjectsManager, TextItem, TouchAndTextItem, ListView

from .input_manager import InputEvent

logger = logging.getLogger(__name__)

try:
    import musicbrainzngs
    _use_musicbrainz = True
    musicbrainzngs.set_useragent(
        "mopidy-touchtft",
        "1.1.0"
        "https://github.com/woelfisch/mopidy-touchscreen"
    )
except:
    _use_musicbrainz = False
    logger.info('Module musicbrainz-ngs not found. Will not download cover art.')

class BaseScreen:
    update_all = 0
    update_partial = 1
    no_update = 2

    def __init__(self, size, base_size, manager, fonts):
        self.size = size
        self.base_size = base_size
        self.manager = manager
        self.fonts = fonts

    def find_update_rects(self, rects):
        pass

    def update(self, surface, update_type, rects):
        """
        Draw this screen to the surface

        :param surface:
        :param update_type:
        :param rects:
        """
        pass

    def event(self, event):
        pass

    def change_screen(self, direction):
        return False

    def should_update(self):
        return BaseScreen.update_partial


class Keyboard(BaseScreen):

    def __init__(self, size, base_size, manager, fonts, listener):
        BaseScreen.__init__(self, size, base_size, manager, fonts)
        self.base_width = size[0] / 10
        self.base_height = size[1] / 5
        self.listener = listener
        self.manager = manager
        self.selected_row = 0
        self.selected_col = 0
        self.selected_others = -1
        self.font = pygame.font.SysFont("arial", int(size[1] / 7))
        self.keyboards = [ScreenObjectsManager(), ScreenObjectsManager()]
        self.other_objects = ScreenObjectsManager()
        self.current_keyboard = 0

        self.keys = [[['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
                      ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '-'],
                      [',', 'z', 'x', 'c', 'v', 'b', 'n', 'm', '.', '_']],

                     [['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
                      ['!', '@', '#', '$', '%', '&', '/', '(', ')', '='],
                      ['?', '{', '}', '_', '[', ']', '+', '<', '>', '*']]]

        line = self.base_height
        for row in self.keys[self.current_keyboard]:
            pos = 0
            for key in row:
                button = \
                    TouchAndTextItem(self.font, key,
                                     (pos, line),
                                     (self.base_width, self.base_height),
                                     center=True, background=(150, 150, 150))
                self.keyboards[self.current_keyboard]. \
                    set_touch_object(key, button)
                pos += self.base_width
            line += self.base_height

        self.current_keyboard = 1
        line = self.base_height
        for row in self.keys[self.current_keyboard]:
            pos = 0
            for key in row:
                button = \
                    TouchAndTextItem(self.font, key, (pos, line),
                                     (self.base_width, self.base_height),
                                     center=True, background=(150, 150, 150),
                                     scroll_no_fit=False)
                self.keyboards[self.current_keyboard]. \
                    set_touch_object(key, button)
                pos += self.base_width
            line += self.base_height
        self.current_keyboard = 0

        # Symbol button
        button = TouchAndTextItem(self.font, "123",
                                  (0, self.base_height * 4), (self.base_width * 2, self.base_height),
                                  center=True, background=(150, 150, 150), scroll_no_fit=False)
        self.other_objects.set_touch_object("symbols", button)

        # remove button
        button = TouchAndTextItem(self.font, "<-",
                                  (self.base_width * 2, self.base_height * 4), (self.base_width * 2, self.base_height),
                                  center=True, background=(150, 150, 150), scroll_no_fit=False)
        self.other_objects.set_touch_object("remove", button)

        # Space button
        button = TouchAndTextItem(self.font, " ",
                                  (self.base_width * 4, self.base_height * 4), (self.base_width * 4, self.base_height),
                                  center=True, background=(150, 150, 150), scroll_no_fit=False)
        self.other_objects.set_touch_object("space", button)

        # OK button
        button = TouchAndTextItem(self.font, "->",
                                  (self.base_width * 8, self.base_height * 4), (self.base_width * 2, self.base_height),
                                  center=True, background=(150, 150, 150), scroll_no_fit=False)
        self.other_objects.set_touch_object("ok", button)

        # EditText button
        button = TouchAndTextItem(self.font, "",
                                  (0, 0), (self.size[0], self.base_height), center=False, scroll_no_fit=False)
        self.other_objects.set_object("text", button)
        self.selected_others = 3
        self.set_selected_other()

    def update(self, screen, update_type, rects):
        screen.fill((0, 0, 0))
        self.keyboards[self.current_keyboard].render(screen)
        self.other_objects.render(screen)

    def touch_event(self, touch_event):
        if touch_event.type == InputEvent.action.click:
            keys = self.keyboards[self.current_keyboard].get_touch_objects_in_pos(touch_event.current_pos)
            for key in keys:
                self.other_objects.get_object("text").add_text(key, False)
            keys = self.other_objects.get_touch_objects_in_pos(touch_event.current_pos)
            for key in keys:
                if key == 'symbols':
                    self.change_keyboard()
                elif key == "remove":
                    self.other_objects.get_object("text").remove_text(1, False)
                elif key == "space":
                    self.other_objects.get_object("text").add_text(" ", False)
                elif key == "ok":
                    text = self.other_objects.get_object("text").text
                    self.listener.text_input(text)
                    self.manager.close_keyboard()
        elif touch_event.type == InputEvent.action.key_press:
            if not isinstance(touch_event.unicode, int):
                if touch_event.unicode == u'\x08':
                    self.other_objects.get_object("text").remove_text(1, False)
                else:
                    self.other_objects.get_object("text").add_text(touch_event.unicode, False)
            elif touch_event.direction is not None:
                x = 0
                y = 0
                if touch_event.direction == InputEvent.course.left:
                    x = -1
                elif touch_event.direction == InputEvent.course.right:
                    x = 1
                elif touch_event.direction == InputEvent.course.up:
                    y = -1
                elif touch_event.direction == InputEvent.course.down:
                    y = 1
                if touch_event.direction == InputEvent.course.enter:
                    self.selected_click()
                else:
                    self.change_selected(x, y)

    def change_keyboard(self):
        if self.current_keyboard == 0:
            self.current_keyboard = 1
        else:
            self.current_keyboard = 0
        if self.selected_others < 0:
            self.change_selected(0, 0)

    def change_selected(self, x, y):
        if self.selected_others < 0:
            # We are on the keyboard

            # Update col
            self.selected_col += x
            if self.selected_col < 0:
                self.selected_col = 0
            elif self.selected_col > 9:
                self.selected_col = 9

            # Update row
            self.selected_row += y
            if self.selected_row < 0:
                self.selected_row = 0
            elif self.selected_row > 2:

                # Change to the bottom part
                if self.selected_col < 2:
                    self.selected_others = 0
                elif self.selected_col < 4:
                    self.selected_others = 1
                elif self.selected_col < 8:
                    self.selected_others = 2
                else:
                    self.selected_others = 3

            # Update selected
            if self.selected_others < 0:
                key = self.keys[self.current_keyboard][
                    self.selected_row][self.selected_col]
                self.keyboards[self.current_keyboard].set_selected(key)
            else:
                self.keyboards[0].set_selected(None)
                self.keyboards[1].set_selected(None)
                self.set_selected_other()
        else:
            # We are on the bottom part
            if y < 0:
                # we are returning to the keyboard

                # Select col
                if self.selected_others == 0:
                    self.selected_col = 0
                elif self.selected_others == 1:
                    self.selected_col = 2
                elif self.selected_others == 2:
                    self.selected_col = 4
                else:
                    self.selected_col = 8

                self.selected_others = -1
                self.set_selected_other()

                self.selected_row = 2
                key = self.keys[self.current_keyboard][
                    self.selected_row][self.selected_col]
                self.keyboards[self.current_keyboard].set_selected(key)
            elif x != 0:
                # We change in horizontal
                self.selected_others += x
                if self.selected_others < 0:
                    self.selected_others = 0
                elif self.selected_others > 3:
                    self.selected_others = 3
                self.set_selected_other()

    def selected_click(self):
        if self.selected_others >= 0:
            if self.selected_others == 0:
                self.change_keyboard()
            elif self.selected_others == 1:
                self.other_objects.get_object("text").remove_text(1, False)
            elif self.selected_others == 2:
                self.other_objects.get_object("text").add_text(" ", False)
            elif self.selected_others == 3:
                text = self.other_objects.get_object("text").text
                self.listener.text_input(text)
                self.manager.close_keyboard()
        else:
            key = self.keys[self.current_keyboard][
                self.selected_row][self.selected_col]
            self.other_objects.get_object("text").add_text(key, False)

    def set_selected_other(self):
        key = None
        if self.selected_others == 0:
            key = "symbols"
        elif self.selected_others == 1:
            key = "remove"
        elif self.selected_others == 2:
            key = "space"
        elif self.selected_others == 3:
            key = "ok"
        self.other_objects.set_selected(key)

class LibraryScreen(BaseScreen):
    def __init__(self, size, base_size, manager, fonts):
        BaseScreen.__init__(self, size, base_size, manager, fonts)
        self.list_view = ListView((0, 0), self.size, self.base_size, self.fonts['base'])
        self.directory_list = []
        self.current_directory = None
        self.library = None
        self.library_strings = None
        self.browse_uri(None)

    def go_inside_directory(self, uri):
        self.directory_list.append(self.current_directory)
        self.current_directory = uri
        self.browse_uri(uri)

    def browse_uri(self, uri):
        self.library_strings = []
        if uri is not None:
            self.library_strings.append("../")
        self.library = self.manager.core.library.browse(uri).get()
        for lib in self.library:
            self.library_strings.append(lib.name)
        self.list_view.set_list(self.library_strings)

    def go_up_directory(self):
        if len(self.directory_list):
            directory = self.directory_list.pop()
            self.current_directory = directory
            self.browse_uri(directory)

    def should_update(self):
        return self.list_view.should_update()

    def find_update_rects(self, rects):
        return self.list_view.find_update_rects(rects)

    def update(self, screen, update_type, rects):
        update_all = (update_type == BaseScreen.update_all)
        self.list_view.render(screen, update_all, rects)

    def touch_event(self, touch_event):
        clicked = self.list_view.touch_event(touch_event)
        if clicked is not None:
            if self.current_directory is not None:
                if clicked == 0:
                    self.go_up_directory()
                else:
                    if self.library[clicked - 1].type == mopidy.models.Ref.TRACK:
                        self.play_uri(clicked - 1)
                    else:
                        self.go_inside_directory(
                            self.library[clicked - 1].uri)
            else:
                self.go_inside_directory(self.library[clicked].uri)

    def play_uri(self, track_pos):
        self.manager.core.tracklist.clear()
        tracks = []
        for item in self.library:
            if item.type == mopidy.models.Ref.TRACK:
                # contrary to the API docs LibraryController.lookup() returns a dict instead of a list
                track_dict = self.manager.core.library.lookup([item.uri]).get()
                # ...and that stupid dict contains file, list(Track) mappings. WTF?!
                track = list(track_dict.values())[0][0]
                logger.debug(f'track is {type(track)} {track}')
                tracks.append(track)
            else:
                track_pos -= 1
        self.manager.core.tracklist.add(tracks=tracks)
        self.manager.core.playback.play(tl_track=self.manager.core.tracklist.get_tl_tracks().get()[track_pos])


class MainScreen(BaseScreen):
    def __init__(self, size, base_size, manager, fonts, cache, core,
                 background):
        BaseScreen.__init__(self, size, base_size, manager, fonts)
        self.core = core
        self.track = None
        self.cache = cache
        self.image = None
        self.artists = None
        self.update_next_frame = True
        self.background = background
        self.update_keys = []
        self.current_track_pos = 0
        self.track_duration = "00:00"
        self.has_to_update_progress = False
        self.touch_text_manager = ScreenObjectsManager()
        current_track = self.core.playback.get_current_track().get()
        if current_track is None:
            self.track_playback_ended(None, None)
        else:
            self.track_started(current_track)

        # Top bar
        self.top_bar = pygame.Surface((self.size[0], self.base_size), pygame.SRCALPHA)
        self.top_bar.fill((0, 0, 0, 128))

        # Play/pause
        button = TouchAndTextItem(self.fonts['icon'], u"\ue615 ", (0, 0), None)
        self.touch_text_manager.set_touch_object("pause_play", button)
        x = button.get_right_pos()

        # Mute
        button = TouchAndTextItem(self.fonts['icon'], u"\ue61f ", (x, 0), None)
        self.touch_text_manager.set_touch_object("mute", button)
        x = button.get_right_pos()

        # Volume
        progress = Progressbar(self.fonts['base'], "100", (x, 0), (self.size[0] - x, self.base_size), 100, True)
        self.touch_text_manager.set_touch_object("volume", progress)
        progress.set_value(self.core.mixer.get_volume().get())
        self.progress_show = False

    def should_update(self):
        if len(self.update_keys) > 0:
            if self.update_progress():
                self.has_to_update_progress = True
            return True
        else:
            if self.progress_show:
                if self.update_progress():
                    self.has_to_update_progress = True
                    return True
                else:
                    return False
            else:
                return False

    def find_update_rects(self, rects):
        for key in self.update_keys:
            item = self.touch_text_manager.get_object(key)
            rects.append(item.rect_in_pos)
        if self.progress_show and self.has_to_update_progress:
            item = self.touch_text_manager.get_touch_object("time_progress")
            rects.append(item.rect_in_pos)

    def update(self, screen, update_type, rects):
        if update_type == BaseScreen.update_all:
            screen.blit(self.top_bar, (0, 0))
            self.update_progress()
            self.has_to_update_progress = False
            self.touch_text_manager.render(screen)
            if self.image is not None:
                screen.blit(self.image, (self.base_size / 2, self.base_size + self.base_size / 2))

        if update_type == BaseScreen.update_partial and self.track is not None:
            if self.has_to_update_progress:
                self.touch_text_manager.get_touch_object("time_progress").render(screen)
                self.has_to_update_progress = False
            for key in self.update_keys:
                item = self.touch_text_manager.get_object(key)
                item.update()
                item.render(screen)

    def update_progress(self):
        if self.progress_show:
            track_pos_millis = self.core.playback.get_time_position().get()
            new_track_pos = track_pos_millis / 1000

            if new_track_pos != self.current_track_pos:
                progress = self.touch_text_manager.get_touch_object("time_progress")
                progress.set_value(track_pos_millis)
                self.current_track_pos = new_track_pos
                progress.set_text(time.strftime('%M:%S', time.gmtime(self.current_track_pos)) +
                                  "/" + self.track_duration)
                return True
        return False

    def track_started(self, track):
        self.update_keys = []
        self.image = None
        x = self.size[1] - self.base_size * 2
        width = self.size[0] - self.base_size / 2 - x

        # Previous track button
        button = TouchAndTextItem(self.fonts['icon'], u"\ue61c", (0, self.size[1] - self.base_size), None)
        self.touch_text_manager.set_touch_object("previous", button)
        size_1 = button.get_right_pos()

        size_2 = self.fonts['icon'].size(u"\ue61d")[0]
        button = TouchAndTextItem(self.fonts['icon'], u"\ue61d",
                                  (self.size[0] - size_2, self.size[1] - self.base_size),  None)
        self.touch_text_manager.set_touch_object("next", button)

        if track.length is not None:
            self.track_duration = time.strftime('%M:%S', time.gmtime(track.length / 1000))

            # Progress
            progress = Progressbar(self.fonts['base'], time.strftime('%M:%S', time.gmtime(0)) + "/" +
                                   time.strftime('%M:%S', time.gmtime(0)), (size_1, self.size[1] - self.base_size),
                                   (self.size[0] - size_1 - size_2, self.base_size), track.length, False)
            self.touch_text_manager.set_touch_object("time_progress", progress)
            self.progress_show = True
        else:
            self.progress_show = False
            self.touch_text_manager.delete_touch_object("time_progress")

        # Load all artists
        self.artists = []
        for artist in track.artists:
            self.artists.append(artist)

        # Track name
        label = TextItem(self.fonts['base'], MainScreen.get_track_name(track),
                         (x, (self.size[1] - self.base_size * 3) / 2 - self.base_size * 0.5), (width, -1))

        if not label.fit_horizontal:
            self.update_keys.append("track_name")
        self.touch_text_manager.set_object("track_name", label)

        # Album name
        label = TextItem(self.fonts['base'], MainScreen.get_track_album_name(track),
                         (x, (self.size[1] - self.base_size * 3) / 2 + self.base_size * 0.5), (width, -1))

        if not label.fit_horizontal:
            self.update_keys.append("album_name")
        self.touch_text_manager.set_object("album_name", label)

        # Artist
        label = TextItem(self.fonts['base'], self.get_artist_string(),
                         (x, (self.size[1] - self.base_size * 3) / 2 + self.base_size * 1.5), (width, -1))

        if not label.fit_horizontal:
            self.update_keys.append("artist_name")
        self.touch_text_manager.set_object("artist_name", label)

        self.track = track
        if not self.is_image_in_cache():
            thread = Thread(target=self.download_image, name="Download Cover")
            thread.start()
        else:
            thread = Thread(target=self.load_image, name="Load Cover")
            thread.start()

    def stream_title_changed(self, title):
        self.touch_text_manager.get_object("track_name").set_text(title, False)

    def get_artist_string(self):
        artists_string = ''
        for artist in self.artists:
            artists_string += artist.name + ', '
        if len(artists_string) > 2:
            artists_string = artists_string[:-2]
        elif len(artists_string) == 0:
            artists_string = "Unknown Artist"
        return artists_string

    def get_image_file_name(self):
        name = MainScreen.get_track_album_name(
            self.track) + '-' + self.get_artist_string()
        md5name = hashlib.md5(name.encode('utf-8')).hexdigest()
        return md5name

    def get_cover_folder(self):
        if not os.path.isdir(self.cache + "/covers"):
            os.makedirs(self.cache + "/covers")
        return self.cache + "/covers/"

    def is_image_in_cache(self):
        self.get_cover_folder()
        return os.path.isfile(
            self.get_cover_folder() + self.get_image_file_name())

    def download_image(self):
        image_uris = self.core.library.get_images([self.track.uri]).get()[self.track.uri]
        if len(image_uris) > 0:
            urllib.request.urlretrieve(image_uris[0].uri, self.get_cover_folder() + self.get_image_file_name())
            self.load_image()
        else:
            self.download_image_musicbrainz(0)

    def download_image_musicbrainz(self, artist_index):
        found = False
        while _use_musicbrainz and not found and artist_index < len(self.artists):
            result = musicbrainzngs.search_releases(artist=self.artists[artist_index].name,
                                                    release=MainScreen.get_track_album_name(self.track), limit=5)

            releases = result.get('release-list')
            if releases is None or len(releases) < 1:
                logger.info('Artist/Album combination not found on Musicbrainz')
                artist_index += 1
                continue

            for release in releases:
                mbid = release.get("id")
                if mbid is None:
                    logger.info('MusicBrainz error: no MBID')
                    continue

                try:
                    image = musicbrainzngs.get_image_front(mbid, size="500")
                    with open(self.get_cover_folder() + self.get_image_file_name(), "wb") as fp:
                        fp.write(image)
                    self.load_image()
                    found = True
                    break
                except:
                    logger.info(f'Cover art for {mbid} not found')

        if not found:
            logger.info("Cover could not be downloaded")

            # There is no cover
            # so it will use all the screen size for the text
            width = self.size[0] - self.base_size

            current = TextItem(self.fonts['base'], MainScreen.get_track_name(self.track),
                               (self.base_size / 2, self.base_size * 2), (width, -1))

            if not current.fit_horizontal:
                self.update_keys.append("track_name")
            self.touch_text_manager.set_object("track_name", current)

            current = TextItem(self.fonts['base'], MainScreen.get_track_album_name(self.track),
                               (self.base_size / 2, self.base_size * 3), (width, -1))

            if not current.fit_horizontal:
                self.update_keys.append("album_name")
            self.touch_text_manager.set_object("album_name", current)

            current = TextItem(self.fonts['base'], self.get_artist_string(),
                               (self.base_size / 2, self.base_size * 4), (width, -1))

            if not current.fit_horizontal:
                self.update_keys.append("artist_name")
            self.touch_text_manager.set_object("artist_name", current)

            self.background.set_background_image(None)

    def track_playback_ended(self, tl_track, time_position):
        self.background.set_background_image(None)
        self.image = None
        self.track_duration = "00:00"

        width = self.size[0] - self.base_size

        current = TextItem(self.fonts['base'], "", (self.base_size / 2, self.base_size * 2), (width, -1))
        self.touch_text_manager.set_object("track_name", current)

        current = TextItem(self.fonts['base'], "", (self.base_size / 2, self.base_size * 3), (width, -1))
        self.touch_text_manager.set_object("album_name", current)

        current = TextItem(self.fonts['base'], "", (self.base_size / 2, self.base_size * 4), (width, -1))
        self.touch_text_manager.set_object("artist_name", current)

    def load_image(self):
        size = int(self.size[1] - self.base_size * 3)
        image_original = pygame.image.load(self.get_cover_folder() + self.get_image_file_name())
        image = pygame.transform.scale(image_original, (size, size))
        image = image.convert()
        self.image = image
        self.background.set_background_image(image_original)

    def touch_event(self, event):
        if event.type == InputEvent.action.click or event.type == InputEvent.action.long_click:
            objects = self.touch_text_manager.get_touch_objects_in_pos(event.current_pos)
            if objects is not None:
                self.click_on_objects(objects, event)

        elif event.type == InputEvent.action.swipe:
            if event.direction == InputEvent.course.left:
                self.core.playback.next()
            elif event.direction == InputEvent.course.right:
                self.core.playback.previous()
            elif event.direction == InputEvent.course.up:
                volume = self.core.mixer.get_volume().get() + 10
                if volume > 100:
                    volume = 100
                self.core.mixer.set_volume(volume)
            elif event.direction == InputEvent.course.down:
                volume = self.core.mixer.get_volume().get() - 10
                if volume < 0:
                    volume = 0
                self.core.mixer.set_volume(volume)
        elif event.type == InputEvent.action.key_press:
            if event.direction == InputEvent.course.enter:
                self.click_on_objects(["pause_play"], event)
            elif event.direction == InputEvent.course.up:
                vol = self.core.mixer.get_volume().get()
                vol += 3
                if vol > 100:
                    vol = 100
                self.core.mixer.set_volume(vol)
            elif event.direction == InputEvent.course.down:
                vol = self.core.mixer.get_volume().get()
                vol -= 3
                if vol < 0:
                    vol = 0
                self.core.mixer.set_volume(vol)
            elif event.longpress:
                if event.direction == InputEvent.course.left:
                    self.click_on_objects(["previous"], event)
                elif event.direction == InputEvent.course.right:
                    self.click_on_objects(["next"], event)

    def click_on_objects(self, objects, event):
        try:
            assert event is not None
        except AssertionError:
            traceback.print_exc()
            return

        if objects is not None:
            for key in objects:
                if key == "time_progress":
                    value = self.touch_text_manager.get_touch_object(key).get_pos_value(event.current_pos)
                    self.core.playback.seek(value)
                elif key == "previous":
                    self.core.playback.previous()
                elif key == "next":
                    self.core.playback.next()
                elif key == "volume":
                    self.change_volume(event)
                elif key == "pause_play":
                    playback_state = self.core.playback.get_state().get()
                    if event.type == InputEvent.action.long_click:
                        if playback_state != mopidy.core.PlaybackState.STOPPED:
                            self.core.playback.stop()
                        else:
                            self.core.playback.play()
                    else:
                        if playback_state == mopidy.core.PlaybackState.PLAYING:
                            self.core.playback.pause()
                        elif playback_state == mopidy.core.PlaybackState.PAUSED:
                            self.core.playback.resume()
                        elif playback_state == mopidy.core.PlaybackState.STOPPED:
                            self.core.playback.play()
                elif key == "mute":
                    mute = not self.core.mixer.get_mute().get()
                    self.core.mixer.set_mute(mute)
                    self.mute_changed(mute)

    def change_volume(self, event):
        manager = self.touch_text_manager
        volume = manager.get_touch_object("volume")
        pos = event.current_pos
        value = volume.get_pos_value(pos)
        self.core.mixer.set_volume(value)

    def playback_state_changed(self, old_state, new_state):
        if new_state == mopidy.core.PlaybackState.PLAYING:
            self.touch_text_manager.get_touch_object("pause_play").set_text(u"\ue615", False)  # |>
        elif new_state == mopidy.core.PlaybackState.PAUSED:
            self.touch_text_manager.get_touch_object("pause_play").set_text(u"\ue616", False)  # ||
        elif new_state == mopidy.core.PlaybackState.STOPPED:
            self.touch_text_manager.get_touch_object("pause_play").set_text(u"\ue617", False)  # []

    def volume_changed(self, volume):
        if not self.core.mixer.get_mute().get():
            if volume > 80:
                self.touch_text_manager.get_touch_object("mute").set_text(u"\ue61f", False)
            elif volume > 50:
                self.touch_text_manager.get_touch_object("mute").set_text(u"\ue620", False)
            elif volume > 20:
                self.touch_text_manager.get_touch_object("mute").set_text(u"\ue621", False)
            else:
                self.touch_text_manager.get_touch_object("mute").set_text(u"\ue622", False)
        self.touch_text_manager.get_touch_object("volume").set_value(
            volume)

    def mute_changed(self, mute):
        self.touch_text_manager.get_touch_object("mute").set_active(not mute)
        if mute:
            self.touch_text_manager.get_touch_object("mute").set_text(u"\ue623", False)
        else:
            self.volume_changed(self.core.mixer.get_volume().get())

    @staticmethod
    def get_track_name(track):
        if track.name is None:
            return track.uri
        else:
            return track.name

    @staticmethod
    def get_track_album_name(track):
        if track.album is not None and track.album.name is not None and len(track.album.name) > 0:
            return track.album.name
        else:
            return "Unknown Album"


class MenuScreen(BaseScreen):
    def __init__(self, size, base_size, manager, fonts, core):
        BaseScreen.__init__(self, size, base_size, manager, fonts)
        self.ip = None
        self.core = core
        self.list_view = ListView((0, 0), size,
                                  base_size, fonts['base'])

        self.list_items = ["Random", "Repeat", "Single", "Consume",
                           "Exit Mopidy", "Shutdown", "Restart", "IP: "]

        self.list_view.set_list(self.list_items)

    def should_update(self):
        return self.list_view.should_update()

    def find_update_rects(self, rects):
        return self.list_view.find_update_rects(rects)

    def update(self, screen, update_type, rects):
        update_all = (update_type == BaseScreen.update_all)
        self.list_view.render(screen, update_all, rects)

    def touch_event(self, event):
        clicked = self.list_view.touch_event(event)
        if clicked is not None:
            if clicked == 0:
                random = not self.core.tracklist.get_random().get()
                self.core.tracklist.set_random(random)
            elif clicked == 1:
                repeat = not self.core.tracklist.get_repeat().get()
                self.core.tracklist.set_repeat(repeat)
            elif clicked == 2:
                single = not self.core.tracklist.get_single().get()
                self.core.tracklist.set_single(single)
            elif clicked == 3:
                consume = not self.core.tracklist.get_consume().get()
                self.core.tracklist.set_consume(consume)
            elif clicked == 4:
                os.system("pkill mopidy")
            elif clicked == 5:
                if os.system("gksu -- shutdown now -h") != 0:
                    os.system("sudo shutdown now -h")
            elif clicked == 6:
                if os.system("gksu -- shutdown -r now") != 0:
                    os.system("sudo shutdown -r now")
            elif clicked == 7:
                self.check_connection()

    # Will check internet connection
    def check_connection(self):
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.ip = s.getsockname()[0]
            s.close()
            self.list_items[7] = "IP: " + self.ip
            self.list_view.set_list(self.list_items)
        except socket.error:
            if s is not None:
                s.close()
            self.ip = None
            self.list_items[7] = "IP: No internet"
            self.list_view.set_list(self.list_items)

    def options_changed(self):
        active = []
        if self.core.tracklist.get_random().get():
            active.append(0)
        if self.core.tracklist.get_repeat().get():
            active.append(1)
        if self.core.tracklist.get_single().get():
            active.append(2)
        if self.core.tracklist.get_consume().get():
            active.append(3)
        self.list_view.set_active(active)

class PlaylistScreen(BaseScreen):
    def __init__(self, size, base_size, manager, fonts):
        BaseScreen.__init__(self, size, base_size, manager, fonts)
        self.list_view = ListView((0, 0), size, self.base_size,
                                  self.fonts['base'])
        self.playlists_strings = []
        self.playlists = []
        self.selected_playlist = None
        self.playlist_tracks = []
        self.playlist_uris = []
        self.playlist_tracks_strings = []
        self.playlists_loaded()

    def should_update(self):
        return self.list_view.should_update()

    def find_update_rects(self, rects):
        return self.list_view.find_update_rects(rects)

    def update(self, screen, update_type, rects):
        update_all = (update_type == BaseScreen.update_all)
        self.list_view.render(screen, update_all, rects)

    def playlists_loaded(self):
        self.selected_playlist = None
        self.playlists_strings = []
        self.playlists = []
        for playlist in self.manager.core.playlists.as_list().get():
            self.playlists.append(playlist)
            self.playlists_strings.append(playlist.name)
        self.list_view.set_list(self.playlists_strings)

    def playlist_selected(self, playlist):
        self.selected_playlist = playlist
        self.playlist_tracks = []
        self.playlist_uris = []
        self.playlist_tracks_strings = ["../"]
        for ref in self.manager.core.playlists.get_items(playlist.uri).get():
            track = Track(uri=ref.uri, name=ref.name)
            self.playlist_tracks.append(track)
            self.playlist_uris.append(ref.uri)
            if track.name is None:
                self.playlist_tracks_strings.append(ref.uri)
            else:
                self.playlist_tracks_strings.append(ref.name)
        self.list_view.set_list(self.playlist_tracks_strings)

    def touch_event(self, touch_event):
        clicked = self.list_view.touch_event(touch_event)
        logger.debug(f'touch_event: {touch_event}, {clicked}')
        if clicked is not None:
            if self.selected_playlist is None:
                self.playlist_selected(self.playlists[clicked])
            else:
                if clicked == 0:
                    self.selected_playlist = None
                    self.list_view.set_list(self.playlists_strings)
                else:
                    self.manager.core.tracklist.clear()
                    # passing a list of tracks is deprecated, but how else do I get the names in the M3U file into the 
                    # the tracklist for streams that don't have track meta data?
                    # self.manager.core.tracklist.add(uris=self.playlist_uris)
                    self.manager.core.tracklist.add(tracks=self.playlist_tracks)
                    self.manager.core.playback.play(
                        tl_track=self.manager.core.tracklist.get_tl_tracks().get()[clicked - 1])
                    # self.manager.change_screen(self.manager.screen_type.Player)


SearchMode = Enum('SearchMode', 'Track Album Artist')


class SearchScreen(BaseScreen):
    def __init__(self, size, base_size, manager, fonts):
        BaseScreen.__init__(self, size, base_size, manager, fonts)
        self.list_view = ListView((0, self.base_size * 2), (
            self.size[0], self.size[1] -
            2 * self.base_size), self.base_size, manager.fonts['base'])
        self.results_strings = []
        self.results = []
        self.screen_objects = ScreenObjectsManager()
        self.query = ""

        # Search button
        button = TouchAndTextItem(self.fonts['icon'], u" \ue986", (0, self.base_size), None, center=True)
        self.screen_objects.set_touch_object("search", button)

        x = button.get_right_pos()

        # Query text
        text = TouchAndTextItem(self.fonts['base'], self.query, (0, 0), (self.size[0], self.base_size), center=True)
        self.screen_objects.set_touch_object("query", text)

        # Mode buttons
        button_size = ((self.size[0] - x) / 3, self.base_size)
        self.mode_objects_keys = {
            SearchMode.Track: "mode_track",
            SearchMode.Album: "mode_album",
            SearchMode.Artist: "mode_artist"
        }

        # Track button
        button = TouchAndTextItem(self.fonts['base'], "Track",
                                  (x, self.base_size), (button_size[0], self.base_size), center=True)
        self.screen_objects.set_touch_object(
            self.mode_objects_keys[SearchMode.Track], button)

        # Album button
        button = TouchAndTextItem(self.fonts['base'], "Album",
                                  (button_size[0] + x, self.base_size), button_size, center=True)
        self.screen_objects.set_touch_object(
            self.mode_objects_keys[SearchMode.Album], button)

        # Artist button
        button = TouchAndTextItem(self.fonts['base'], "Artist",
                                  (button_size[0] * 2 + x, self.base_size), button_size, center=True)
        self.screen_objects.set_touch_object(
            self.mode_objects_keys[SearchMode.Artist], button)

        # Top Bar
        self.top_bar = pygame.Surface((self.size[0], self.base_size * 2), pygame.SRCALPHA)
        self.top_bar.fill((0, 0, 0, 128))
        self.mode = None
        self.set_mode(mode=SearchMode.Track)
        self.set_query("Search")

    def should_update(self):
        return self.list_view.should_update()

    def find_update_rects(self, rects):
        return self.list_view.find_update_rects(rects)

    def update(self, screen, update_type, rects):
        screen.blit(self.top_bar, (0, 0))
        self.screen_objects.render(screen)
        update_all = (update_type == BaseScreen.update_all)
        self.list_view.render(screen, update_all, rects)

    def set_mode(self, mode=SearchMode.Track):
        if mode is not self.mode:
            self.mode = mode
            for val in self.mode_objects_keys.values():
                self.screen_objects.get_touch_object(val).set_active(False)
            self.screen_objects.get_touch_object(self.mode_objects_keys[self.mode]).set_active(True)
            self.search(self.query, self.mode)

    def set_query(self, query=""):
        self.query = query
        self.screen_objects.get_touch_object("query").set_text(self.query, False)

    def search(self, query=None, mode=None):
        if query is not None:
            self.set_query(query)
        if mode is not None:
            self.set_mode(mode)
        if self.mode == SearchMode.Track:
            search_query = {'any': [self.query]}
        elif self.mode == SearchMode.Album:
            search_query = {'album': [self.query]}
        else:
            search_query = {'artist': [self.query]}
        if len(self.query) > 0:
            logger.debug(f'{search_query}')
            current_results = self.manager.core.library.search(search_query).get()
            self.results = []
            self.results_strings = []
            for backend in current_results:
                if mode == SearchMode.Track:
                    iterable = backend.tracks
                    logger.debug(f'results for tracks: {iterable}')
                elif mode == SearchMode.Album:
                    iterable = backend.albums
                    logger.debug(f'results for albums: {iterable}')
                else:
                    iterable = backend.artists
                    logger.debug(f'results for artists: {iterable}')

                for result in iterable:
                    self.results.append(result)
                    self.results_strings.append(result.name)
            self.list_view.set_list(self.results_strings)

    def touch_event(self, touch_event):
        if touch_event.type == InputEvent.action.click:
            clicked = self.list_view.touch_event(touch_event)
            if clicked is not None:
                self.manager.core.tracklist.clear()
                self.manager.core.tracklist.add(uri=self.results[clicked].uri)
                self.manager.core.playback.play()
            else:
                clicked = self.screen_objects.get_touch_objects_in_pos(touch_event.down_pos)
                if len(clicked) > 0:
                    clicked = clicked[0]
                    if clicked in self.mode_objects_keys.values():
                        mode = [k for k, v in self.mode_object_keys if v == clicked][0]
                        logger.debug(f'mode = {mode}')
                        self.search(mode=mode)
                    if clicked == "query" or clicked == "search":
                        self.manager.open_keyboard(self)
        else:
            pos = self.list_view.touch_event(touch_event)
            if pos is not None:
                self.manager.core.tracklist.clear()
                self.manager.core.tracklist.add(uris=[self.results[pos].uri])
                self.manager.core.playback.play()

    def change_screen(self, direction):
        mode = self.mode.value
        if direction == InputEvent.course.right:
            if mode < SearchMode.Artist.value:
                self.set_mode(SearchMode(mode + 1))
                return True
        elif direction == InputEvent.course.left:
            if mode > SearchMode.Track.value:
                self.set_mode(SearchMode(mode - 1))
                return True
            else:
                self.manager.open_keyboard(self)
        return False

    def text_input(self, text):
        self.search(text, self.mode)


class Tracklist(BaseScreen):
    def __init__(self, size, base_size, manager, fonts):
        BaseScreen.__init__(self, size, base_size, manager, fonts)
        self.size = size
        self.base_size = base_size
        self.manager = manager
        self.list_view = ListView((0, 0), size, self.base_size, self.fonts['base'])
        self.tracks = []
        self.tracks_strings = []
        self.update_list()
        self.track_started(self.manager.core.playback.get_current_tl_track().get())

    def should_update(self):
        return self.list_view.should_update()

    def find_update_rects(self, rects):
        return self.list_view.find_update_rects(rects)

    def update(self, screen, update_type, rects):
        update_all = (update_type == BaseScreen.update_all)
        self.list_view.render(screen, update_all, rects)

    def tracklist_changed(self):
        self.update_list()

    def update_list(self):
        self.tracks = self.manager.core.tracklist.get_tl_tracks().get()
        self.tracks_strings = []
        for tl_track in self.tracks:
            logger.debug(f'tl_track is {tl_track} ({type(tl_track)}), track is {type(tl_track.track)}')
            trackname = MainScreen.get_track_name(tl_track.track)
            logger.debug(f'trackname is {trackname}\n')
            self.tracks_strings.append(trackname)
        self.list_view.set_list(self.tracks_strings)

    def touch_event(self, touch_event):
        pos = self.list_view.touch_event(touch_event)
        if pos is not None:
            self.manager.core.playback.play(self.tracks[pos])

    def track_started(self, track):
        tlindex = self.manager.core.tracklist.index(track).get()
        self.list_view.set_active([tlindex])
