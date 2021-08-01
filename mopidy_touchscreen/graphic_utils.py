import pygame
import logging
import math

from .input_manager import InputManager

logger = logging.getLogger(__name__)

change_speed = 2


class DynamicBackground:

    def __init__(self, size):
        self.image_loaded = False
        self.size = size
        self.surface = pygame.Surface(self.size).convert()
        self.surface.fill((145, 16, 16))
        self.surface_image = pygame.Surface(self.size).convert()
        self.surface_image.fill((145, 16, 16))
        self.surface_image_last = pygame.Surface(self.size).convert()
        self.update = True
        self.screen_change_percent = 100

    def draw_background(self):
        self.update_background()
        return self.surface.copy()

    def draw_background_in_rects(self, surface, rects):
        self.update_background()
        for rect in rects:
            surface.blit(self.surface, rect, area=rect)

    def update_background(self):
        if self.image_loaded:
            if self.screen_change_percent < 255:
                self.surface.fill((0, 0, 0))
                self.surface_image_last.set_alpha(
                    255 - self.screen_change_percent)
                self.surface_image.set_alpha(self.screen_change_percent)
                self.surface.blit(self.surface_image_last, (0, 0))
                self.surface.blit(self.surface_image, (0, 0))
                self.screen_change_percent += 5
                self.update = True

    def should_update(self):
        if self.update:
            self.update = False
            return True
        else:
            return False

    def set_background_image(self, image):
        if image is not None:
            image_size = get_aspect_scale_size(image, self.size)
            target = pygame.transform.smoothscale(image, image_size)
            self.surface_image_last = self.surface_image.copy()
            pos = (int((self.size[0] - image_size[0]) / 2),
                   (int(self.size[1] - image_size[1]) / 2))
            self.surface_image.blit(blur_surf_times(
                target, self.size[0] / 40, 10), pos)
            self.screen_change_percent = 0
            self.image_loaded = True
        self.update = True


def get_aspect_scale_size(img, new_size):
    size = img.get_size()
    aspect_x = new_size[0] / float(size[0])
    aspect_y = new_size[1] / float(size[1])
    if aspect_x > aspect_y:
        aspect = aspect_x
    else:
        aspect = aspect_y
    new_size = (int(aspect * size[0]), int(aspect * size[1]))
    return new_size


def blur_surf_times(surface, amt, times):
    for i in range(times):
        surface = blur_surf(surface, amt)
    return surface


# http://www.akeric.com/blog/?p=720
def blur_surf(surface, amt):
    """
    Blur the given surface by the given 'amount'.  Only values 1 and greater
    are valid.  Value 1 = no blur.
    """

    scale = 1.0 / float(amt)
    surf_size = surface.get_size()
    scale_size = (int(surf_size[0] * scale), int(surf_size[1] * scale))
    surf = pygame.transform.smoothscale(surface, scale_size)
    surf = pygame.transform.smoothscale(surf, surf_size)
    return surf


class ListView:
    def __init__(self, pos, size, base_size, font):
        self.size = size
        self.pos = pos
        self.base_size = base_size
        self.screen_objects = ScreenObjectsManager()
        self.max_rows = int(self.size[1] / font.size("TEXT SIZE")[1])  # DUDE!!!11 font.size() returns a float!
        self.current_item = 0
        self.font = font
        self.list_size = 0
        self.list = []
        self.scrollbar = False
        self.selected = None
        self.active = []
        self.set_list([])
        self.update_keys = []
        self.should_update_always = False
        self.must_update = False

    # Sets the list for the lisview.
    # It should be an iterable of strings
    def set_list(self, item_list):
        self.screen_objects.clear()
        self.list = item_list
        self.list_size = len(item_list)
        if self.max_rows < self.list_size:
            self.scrollbar = True
            scroll_bar = ScrollBar(
                (self.pos[0] + self.size[0] - self.base_size,
                 self.pos[1]),
                (self.base_size, self.size[1]), self.list_size,
                self.max_rows)
            self.screen_objects.set_touch_object("scrollbar",
                                                 scroll_bar)
        else:
            self.scrollbar = False
        if self.list_size > 0:
            self.selected = 0
        else:
            self.selected = None
        self.load_new_item_position(0)

    # Will load items currently displaying in item_pos
    def load_new_item_position(self, item_pos):
        assert (isinstance(item_pos, int))
        self.update_keys = []
        self.current_item = item_pos
        if self.scrollbar:
            self.screen_objects.clear_touch(["scrollbar"])
        else:
            self.screen_objects.clear_touch(None)
        i = self.current_item
        z = 0
        if self.scrollbar:
            width = self.size[0] - self.base_size
        else:
            width = self.size[0]
        self.should_update_always = False
        current_y = self.pos[1]
        while i < self.list_size and current_y <= self.pos[1] + self.size[1]:
            item = TouchAndTextItem(self.font, self.list[i], (
                self.pos[0],
                current_y), (width, -1))
            current_y += item.size[1]
            if not item.fit_horizontal:
                self.update_keys.append(str(i))
            self.screen_objects.set_touch_object(str(i), item)
            i += 1
            z += 1
        self.reload_selected()

    def should_update(self):
        if len(self.update_keys) > 0:
            return True
        else:
            return False

    def find_update_rects(self, rects):
        for key in self.update_keys:
            item = self.screen_objects.get_touch_object(key)
            rects.append(item.rect_in_pos)

    def render(self, surface, update_all, rects):
        if update_all:
            self.screen_objects.render(surface)
        else:
            for key in self.update_keys:
                item = self.screen_objects.get_touch_object(key)
                item.update()
                item.render(surface)

    def touch_event(self, touch_event):
        self.must_update = True
        if touch_event.type == InputManager.click \
                or touch_event.type == InputManager.long_click:
            objects = self.screen_objects.get_touch_objects_in_pos(
                touch_event.current_pos)
            if objects is not None:
                for key in objects:
                    if key == "scrollbar":
                        direction = \
                            self.screen_objects.get_touch_object(
                                key).touch(touch_event.current_pos)
                        if direction != 0:
                            self.move_to(direction)
                    else:
                        return int(key)
        elif (touch_event.type == InputManager.key and
              self.selected is not None):
            if touch_event.direction == InputManager.enter:
                if self.selected is not None:
                    return self.selected
            elif touch_event.direction == InputManager.up:
                self.set_selected(self.selected - 1)
            elif touch_event.direction == InputManager.down:
                self.set_selected(self.selected + 1)
        elif touch_event.type == InputManager.swipe:
            if touch_event.direction == InputManager.up:
                self.move_to(-1)
            elif touch_event.direction == InputManager.down:
                self.move_to(1)

    # Scroll to direction
    # direction == 1 will scroll down
    # direction == -1 will scroll up
    def move_to(self, direction):
        assert (isinstance(self.max_rows, int))
        if self.scrollbar:
            if direction == 1:
                self.current_item += self.max_rows
                if self.current_item + self.max_rows > self.list_size:
                    self.current_item = self.list_size - self.max_rows
                self.load_new_item_position(self.current_item)
                self.screen_objects.get_touch_object(
                    "scrollbar").set_item(
                    self.current_item)
            elif direction == -1:
                self.current_item -= self.max_rows
                if self.current_item < 0:
                    self.current_item = 0
                self.load_new_item_position(self.current_item)
                self.screen_objects.get_touch_object(
                    "scrollbar").set_item(
                    self.current_item)
            self.set_active(self.active)

    # Set active items
    def set_active(self, active):
        self.must_update = True
        for number in self.active:
            try:
                self.screen_objects.get_touch_object(
                    str(number)).set_active(
                    False)
            except KeyError:
                pass
        for number in active:
            try:
                self.screen_objects.get_touch_object(
                    str(number)).set_active(
                    True)
            except KeyError:
                pass
        self.active = active

    def set_selected(self, selected):
        self.must_update = True
        if -1 < selected < len(self.list):
            if self.selected is not None:
                try:
                    self.screen_objects.get_touch_object(
                        str(self.selected)).set_selected(
                        False)
                except KeyError:
                    pass
            if selected is not None:
                try:
                    self.screen_objects.get_touch_object(
                        str(selected)).set_selected(
                        True)
                except KeyError:
                    pass
            self.selected = selected
            self.set_selected_on_screen()

    def set_selected_on_screen(self):
        self.must_update = True
        if self.current_item + self.max_rows <= self.selected:
            self.move_to(1)
            self.set_selected_on_screen()
        elif self.current_item > self.selected:
            self.move_to(-1)
            self.set_selected_on_screen()

    def reload_selected(self):
        self.must_update = True
        if self.selected is not None:
            try:
                self.screen_objects.get_touch_object(
                    str(self.selected)).set_selected(
                    True)
            except KeyError:
                pass


class ScreenObjectsManager:
    def __init__(self):
        self.touch_objects = {}
        self.text_objects = {}
        self.selected = None
        self.selected_key = None

    def clear(self):
        self.touch_objects = {}
        self.text_objects = {}

    def set_object(self, key, add_object):
        self.text_objects[key] = add_object

    def get_object(self, key):
        return self.text_objects[key]

    def set_touch_object(self, key, add_object):
        self.touch_objects[key] = add_object

    def delete_touch_object(self, key):
        try:
            del self.touch_objects[key]
        except KeyError:
            pass

    def get_touch_object(self, key):
        return self.touch_objects[key]

    def render(self, surface):
        for idx_text in self.text_objects:
            self.text_objects[idx_text].update()
            self.text_objects[idx_text].render(surface)
        for idx_touch in self.touch_objects:
            self.touch_objects[idx_touch].update()
            self.touch_objects[idx_touch].render(surface)

    def get_touch_objects_in_pos(self, pos):
        touched_objects = []
        for key in self.touch_objects:
            if self.touch_objects[key].is_pos_inside(pos):
                touched_objects.append(key)
        return touched_objects

    def clear_touch(self, not_remove):
        if not_remove is not None:
            new_touch = {}
            for key in not_remove:
                new_touch[key] = self.get_touch_object(key)
            self.touch_objects = new_touch
        else:
            self.touch_objects = {}

    def set_selected(self, key):
        if self.selected is not None:
            self.selected.set_selected(False)
        if key is not None:
            self.selected = self.touch_objects[key]
            self.selected.set_selected(True)
            self.selected_key = key
        else:
            self.selected = None
            self.selected_key = None


class BaseItem:
    def __init__(self, pos, size):
        self.pos = pos
        self.size = size
        self.rect = pygame.Rect(0, 0, self.size[0], self.size[1])
        self.rect_in_pos = pygame.Rect(self.pos[0], self.pos[1],
                                       self.size[0],
                                       self.size[1])

    def get_right_pos(self):
        return self.pos[0] + self.size[0]

    def update(self):
        return False


class TextItem(BaseItem):
    scroll_speed = 2

    def __init__(self, font, text, pos, size, center=False, background=None,
                 scroll_no_fit=True):

        logger.debug(f'type of text is {type(text)}')

        self.font = font
        self.text = text
        self.scroll_no_fit = scroll_no_fit
        self.color = (255, 255, 255)
        self.box = self.font.render(text, True, self.color)
        self.box = self.box.convert_alpha()
        self.background = background
        if size is not None:
            if size[1] == -1:
                height = self.font.size(text)[1]
                BaseItem.__init__(self, pos, (size[0], height))
            else:
                BaseItem.__init__(self, pos, size)
        else:
            BaseItem.__init__(self, pos, self.font.size(text))
        if size is not None:
            if self.pos[0] + self.box.get_rect().width > pos[0] + \
                    size[0]:
                self.fit_horizontal = False
                self.step = 0
                self.step_2 = None
                self.scroll_white_gap = self.font.get_height() * 4
            else:
                self.fit_horizontal = True
            if self.pos[1] + self.box.get_rect().height > pos[1] + \
                    size[1]:
                self.fit_vertical = False
            else:
                self.fit_vertical = True
        else:
            self.fit_horizontal = True
            self.fit_vertical = True
        self.margin = 0
        self.center = center
        if self.center:
            if self.fit_horizontal:
                self.margin = (self.size[0] -
                               self.box.get_rect().width) / 2

    def update(self):
        if self.scroll_no_fit and not self.fit_horizontal:
            self.step += TextItem.scroll_speed
            if self.step_2 is None:
                if (self.box.get_rect().width - self.step +
                    self.scroll_white_gap) < self.size[0]:
                    self.step_2 = \
                        self.box.get_rect().width - \
                        self.step + self.scroll_white_gap
            else:
                self.step_2 -= TextItem.scroll_speed
                if self.step_2 < 0:
                    self.step = 0 - self.step_2
                    self.step_2 = None
            return True
        else:
            return BaseItem.update(self)

    def render(self, surface):
        if self.background:
            surface.fill(self.background, rect=self.rect_in_pos)
            pygame.draw.rect(surface, (0, 0, 0), self.rect_in_pos, 1)
        if self.fit_horizontal:
            surface.blit(
                self.box, ((self.pos[0] + self.margin),
                           self.pos[1]), area=self.rect)
        else:
            if self.scroll_no_fit:
                surface.blit(self.box, self.pos,
                             area=pygame.Rect(self.step, 0, self.size[0],
                                              self.size[1]))
                if self.step_2 is not None:
                    surface.blit(self.box, (self.pos[0] + self.step_2,
                                            self.pos[1]),
                                 area=pygame.Rect(0, 0,
                                                  self.size[0] -
                                                  self.step_2,
                                                  self.size[1]))
            else:
                step = self.box.get_rect().width - self.size[0]
                surface.blit(self.box, self.pos,
                             area=pygame.Rect(step, 0, self.size[0],
                                              self.size[1]))

    def set_text(self, text, change_size):
        if text != self.text:
            if change_size:
                TextItem.__init__(self, self.font, text, self.pos,
                                  None, self.center, self.background,
                                  self.scroll_no_fit)
            else:
                TextItem.__init__(self, self.font, text, self.pos,
                                  self.size, self.center, self.background,
                                  self.scroll_no_fit)

    def add_text(self, add_text, change_size):
        self.set_text(self.text + add_text, change_size)

    def remove_text(self, chars, change_size):
        self.set_text(self.text[:-chars], change_size)


class TouchObject(BaseItem):
    def __init__(self, pos, size):
        BaseItem.__init__(self, pos, size)
        self.active = False
        self.selected = False
        self.selected_box = pygame.Surface(size, pygame.SRCALPHA)
        self.selected_box = self.selected_box.convert_alpha()
        self.selected_box.fill((0, 0, 0, 128))
        self.selected_box_rectangle = pygame.Surface(size, pygame.SRCALPHA)
        self.selected_box_rectangle = \
            self.selected_box_rectangle.convert_alpha()
        pygame.draw.rect(self.selected_box_rectangle, (255, 255, 255),
                         self.selected_box_rectangle.get_rect(),
                         int(size[1] / 10) + 1)

    def is_pos_inside(self, pos):
        return self.rect_in_pos.collidepoint(pos)

    def set_active(self, active):
        self.active = active

    def set_selected(self, selected):
        self.selected = selected

    def render(self, surface):
        if self.selected:
            surface.blit(self.selected_box, self.pos)
            surface.blit(self.selected_box_rectangle, self.pos)

    def pre_render(self, surface):
        if self.selected:
            surface.blit(self.selected_box, self.pos)

    def post_render(self, surface):
        if self.selected:
            surface.blit(self.selected_box_rectangle, self.pos)


class TouchAndTextItem(TouchObject, TextItem):
    def __init__(self, font, text, pos, size, center=False, background=None,
                 scroll_no_fit=True):
        TextItem.__init__(self, font, text, pos, size, center=center,
                          background=background, scroll_no_fit=scroll_no_fit)
        TouchObject.__init__(self, pos, self.size)
        self.active_color = (0, 150, 255)
        self.normal_box = self.box
        self.active_box = self.font.render(text, True,
                                           self.active_color)

    def update(self):
        return TextItem.update(self)

    def set_text(self, text, change_size):
        TextItem.set_text(self, text, change_size)
        self.normal_box = self.box
        self.active_box = self.font.render(text, True,
                                           self.active_color)

    def set_active(self, active):
        TouchObject.set_active(self, active)
        if self.active:
            self.box = self.active_box
        else:
            self.box = self.normal_box

    def render(self, surface):
        TouchObject.pre_render(self, surface)
        TextItem.render(self, surface)
        TouchObject.post_render(self, surface)


class Progressbar(TouchObject):
    def __init__(self, font, text, pos, size, max_value, value_text):
        BaseItem.__init__(self, pos, size)
        self.value = 0
        self.max = max_value
        self.back_color = (0, 0, 0, 128)
        self.main_color = (0, 150, 255, 150)
        self.surface = pygame.Surface(self.size, pygame.SRCALPHA) \
            .convert_alpha()
        self.surface.fill(self.back_color)
        self.value_text = value_text

        self.text = TextItem(font, str(max_value), pos, None)
        self.text.set_text(str(self.value), True)

        # Rectangle
        self.rectangle = pygame.Surface(size, pygame.SRCALPHA) \
            .convert_alpha()
        pygame.draw.rect(self.rectangle, (255, 255, 255),
                         self.rectangle.get_rect(),
                         int(size[1] / 20) + 1)

    def render(self, surface):
        surface.blit(self.surface, self.pos)
        surface.blit(self.rectangle, self.pos)
        self.text.render(surface)

    def set_value(self, value):
        if value != self.value:
            self.value = value
            if self.value_text:
                self.set_text(str(self.value))
            self.surface.fill(self.back_color)
            pos_pixel = value * self.size[0] / self.max
            rect = pygame.Rect(0, 0, pos_pixel, self.size[1])
            self.surface.fill(self.main_color, rect)

    def get_pos_value(self, pos):
        x = pos[0] - self.pos[0]
        return x * self.max / self.size[0]

    def set_text(self, text):
        self.text.set_text(text, True)
        self.text.pos = (self.pos[0] + self.size[0] / 2 - self.text.size[0] / 2,
                         self.pos[1] + self.size[1] / 2 - self.text.size[1] / 2)


class ScrollBar(TouchObject):
    def __init__(self, pos, size, max_value, items_on_screen):
        BaseItem.__init__(self, pos,
                          (pos[0] + size[0], pos[1] + size[1]))
        self.pos = pos
        self.size = size
        self.max = max_value
        self.items_on_screen = items_on_screen
        self.current_item = 0
        self.back_bar = pygame.Surface(self.size, pygame.SRCALPHA) \
            .convert_alpha()
        self.back_bar.fill((255, 255, 255, 128))
        self.bar_pos = 0
        if self.max < 1:
            self.bar_size = self.size[1]
        else:
            self.bar_size = math.ceil(
                float(self.items_on_screen) / float(self.max) * float(
                    self.size[1]))
        self.bar = pygame.Surface((self.size[0], self.bar_size)).convert()
        self.bar.fill((255, 255, 255))

    def render(self, surface):
        surface.blit(self.back_bar, self.pos)
        surface.blit(self.bar,
                     (self.pos[0], self.pos[1] + self.bar_pos))

    def touch(self, pos):
        if pos[1] < self.pos[1] + self.bar_pos:
            return -1
        elif pos[1] > self.pos[1] + self.bar_pos + self.bar_size:
            return 1
        else:
            return 0

    def set_item(self, current_item):
        assert (isinstance(current_item, int))
        self.current_item = current_item
        self.bar_pos = float(self.current_item) / float(
            self.max) * float(
            self.size[1])
