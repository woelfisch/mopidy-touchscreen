******************
Mopidy-Touchscreen
******************

This is a port of 9and3r's original TFT Touchscreen extension for Mopidy
to Mopidy 3.2, Python3 and SDL2. A number of other changes have been applied
as well, see below. But it still looks the same:


.. image:: https://img.shields.io/pypi/v/Mopidy-Touchscreen.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Touchscreen/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/Mopidy-Touchscreen.svg?style=flat
    :target: https://pypi.python.org/pypi/Mopidy-Touchscreen/
    :alt: Number of PyPI downloads

.. image:: https://img.shields.io/travis/9and3r/mopidy-touchscreen/develop.svg?style=flat
    :target: https://travis-ci.org/9and3r/mopidy-touchscreen
    :alt: Travis CI build status

.. image:: https://img.shields.io/coveralls/9and3r/mopidy-touchscreen/develop.svg?style=flat
   :target: https://coveralls.io/r/9and3r/mopidy-touchscreen?branch=develop
   :alt: Test coverage

Extension for displaying track info and controlling Mopidy from a touch screen
using `PyGame <http://www.pygame.org/>`_/SDL.

Album Cover images are downloaded from the Cover Art Archive
`<https://coverartarchive.org/>`_ with the help of MusicBrainz
`<https://musicbrainz.org/>`_ and the musicbrainzngs module
`<https://python-musicbrainzngs.readthedocs.io/en/v0.7.1/>`_

Dependencies
============

- ``Mopidy`` >= 3.2
- ``Pykka`` >= 3.0
- ``pygame`` >= 2.1
- ``musicbrainzngs`` >= 0.7.1
- ``SDL2`` >= 2.0.21 (see below for required patch)

Installation
============

Install by running::

   python3 setup.py install

Basic Configuration
===================

Before starting Mopidy, you must add configuration for
Mopidy-Touchscreen to your Mopidy configuration file::

    [touchscreen]
    enabled = true
    screen_width = 320
    screen_height = 240
    resolution_factor = 8
    cursor = True
    fullscreen = False
    cache_dir = $XDG_CACHE_DIR/mopidy/touchscreen

The following configuration values are available:

- ``touchscreen/enabled``: If the Touchscreen extension should be enabled or not.

- ``touchscreen/screen_width``: The width of the resolution you want to use in pixels.

- ``touchscreen/screen_height``: The width of the resolution you want to use in pixels.

- ``touchscreen/resolution_factor``: This value sets how big content is shown. Smaller values will make content bigger and less content will be displayed at once.

- ``touchscreen/cursor``: If the mouse cursor should be shown. (If you use a touchscreen it should be false)

- ``touchscreen/fullscreen``: If you want to be shown as a window or in fullscreen.

- ``touchscreen/cache_dir``: The folder to be used as cache. Defaults to ``$XDG_CACHE_DIR/mopidy/touchscreen``, which usually means `~/.cache/mopidy/touchscreen``

- ``sdl_videodriver``: Sets the ``SDL_VIDEODRIVER`` environment variable.

- ``sdl_video_render_driver``: Sets the renderer for the video driver (e.g., ``opengl``, ``opengles``, ``opengles2`` or ``software``) via the ``SDL_RENDER_DRIVER`` environment variable.

- ``sdl_video_device_index``: Sets the number of the DRI device, if libSDL2 has been patched accordingly to support the ``SDL_VIDEO_DEVICE`` env var (counts from zero, which is *usually* the HDMI output of an RPi)

- ``sdl_video_device``: Sometimes the numbering is **not** stable, though. Use the basename of /dev/dri/by-path/platform-*-card for persistent names over reboots.

- ``sdl_audiodriver``: Sets the ``SDL_AUDIODRIVER`` environment variable

- ``sdl_path_dsp``: Sets the ``SDL_PATH_DSP`` environment variable

- ``sdl_mousedriver``: Sets the ``SDL_MOUSEDRV`` environment variable. This has been renamed from ``sdl_mousdrv``

- ``sdl_mousedev``: Sets the ``SDL_MOUSEDEV`` environment variable. This has been renamed from ``sdl_mousdev``.

- ``start_screen``: The menu screen Mopidy shows on start can be configured. Valid options are ``search``, ``player``, ``tracklist``,  ``library``, ``playlists`` and ``menu``

- ``main_screen``: This is the menu screen Mopidy will return to after twenty seconds of no tap, button or key press. Choices as with ``start_screen``, plus ``none`` to disable.


How to Setup
============

Use the basic configuration to setup as most standard screens works fine without further configuration.

Running Mopidy without root privileges
--------------------------------------

It's recommended to create an unprivileged user ``mopdiy``. Add this user to the ``video`` and ``input`` groups.

LCD Shields
-----------

If you are using a LCD Shield in Raspberry Pi you need to config your LCD:

Configure your LCD Shield
^^^^^^^^^^^^^^^^^^^^^^^^^

Framebuffer devices are about to go away and being replaced by KMSDRM. As of now (March 2022, Debian release 11,
"bullseye"), you'll have to modify and build libSDL from Git, as the one delivered with Debian stale crashes, and even
the upstream version does not support multiple display adapters yet. The latter can be rectified with PR 5276 by user
"substring", https://github.com/libsdl-org/SDL/pull/5276 A rebased version of the patch for 6d1c3cd is in file
``sdl2-device-index-env.diff`` in this repository.

Debian "bullseye" does not come with a device tree overlay for the ILI9341 tinydrm driver yet (rpi-display is for the
old framebuffer driver.) The file ``ili9341-tiny-display.dts`` contains the source of an adjusted overlay file, based
on a suggestion by user "6by9" of forums.raspberrypi.com. Unfortunately, it doesn't allow setting the brightness of the
backlight, only turning it on.

Compile the overlay with

  dtc -I dts ili9341-tiny-display.dts -o /boot/overlays/ili9341-tiny-display.dtbo -O dtb

And configure the driver in /boot/config.txt, for example with:

    dtoverlay=ili9341-tiny-display

The overlay comes with support for an ADS7846 touch controller on SPI 1.

Add to the config the next variables::

    [touchscreen]
    sdl_videodriver = kmsdrm
    sdl_video_render_driver = software
    sdl_video_device = platform-3f204000.spi-cs-0-card

This is just an example. It may work but each LCD Shield seems to have its own configuration.


GPIO Buttons
------------

Native GPIO support has been removed, you can define GPIO inputs as input devices in ``/boot/config.txt`` these days, for example: ::

  dtoverlay=gpio-key,gpio=13,keycode=105,active_low=1,gpio_pull=up        # left
  dtoverlay=gpio-key,gpio=6,keycode=106,active_low=1,gpio_pull=up         # right
  dtoverlay=gpio-key,gpio=19,keycode=103,active_low=1,gpio_pull=up        # up
  dtoverlay=gpio-key,gpio=26,keycode=108,active_low=1,gpio_pull=up        # down
  dtoverlay=gpio-key,gpio=1,keycode=28,active_low=1,gpio_pull=up          # enter
  dtoverlay=gpio-key,gpio=0,keycode=114,active_low=1,gpio_pull=up         # -
  dtoverlay=gpio-key,gpio=5,keycode=115,active_low=1,gpio_pull=up         # +
  dtoverlay=gpio-key,gpio=3,keycode=116,active_low=1,gpio_pull=up         # shutdown

The actual GPIO port (BCM numbering for RPi) depends on your wiring. See https://pinout.xyz/ if unsure.

As you can see from this example, pins should be active low (ie, button press connects the pin to ground)

Other considerations
====================

The audio setup has changed with *bullseye*, if you're using the current VC4 (``vc4-kms-v3d``) DRM video driver and
need HDMI sound output. In this case you may want to disable the BCM2835 line out by commenting out
``dtparam=audio=on`` in ``/boot/config.txt``. More importantly, VC4 HDMI audio has no built-in conversion from any
commonly used data formats, it expects all sound data in IEC958 LE ("raw" S/PDIF) format. Do not use the legacy
FKMS (/dev/fb*) based ``vc4-fkms-v3d`` driver, it will stop working eventually. Raspberrypi OS comes with an ALSA
configuration that contains a converter, but it's a PITA to use. I'm using pulseaudio run as a system service, here's
a systemd unit file: ::

  [Unit]
  Description=PulseAudio Daemon
  [Install]
  WantedBy=sound.target
  [Service]
  Type=simple
  PrivateTmp=true
  ExecStart=/usr/bin/pulseaudio --system --realtime --no-cpu-limit

Don't forget to set up the Unix groups properly as described in
https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/SystemWide/


How To Use
==========

You can use it with a touchscreen or mouse clicking on the icons.

In case you are using a keyboard use arrow keys to navigate and enter to select. The GPIO and LIRC (IR remote control) buttons  simulate keyboard keys so the use is exactly the same as using a keyboard.


Features
========

* See track info (track name, album, artist, cover image)
* Seek Track
* Play/Pause/Stop
* Mute/Unmute
* Change volume
* Next/Previous track
* Library
* Menu (exit mopidy, restart...)
* Shuffle on/off
* Repeat one/on/off
* Playback list and song selection
* Playlists
* Use keyboard. GPIO buttons or IR remote control instead of touchscreen


Video
=====

`Example video running the extension <https://www.youtube.com/watch?v=KuYoIb8Q2LI>`_

Authors
=======

- 9and3r (http://github.com/9and3r): 
  Original author and maintainer for many years. Thanks!

- Joerg Reuter (http://github.com/woelfisch): 
  Port to Python 3, Mopidy 3.2, bug fixes, new bugs

Changelog
=========

2022-03-29 (woelfisch fork)
---------------------------

- libSDL2 has support for KMSDRM now. Yay. libSDL2 still needs a patch to use other video
  devices than the first. Boo. Supporting additional SDL environment variables
- Added rebase of said patch
- Subsequently, removed support for /dev/fb* again
- Removed evdev support again, SDL2 handles the GPIO keys and lirc/ir_keytable remotes just fine
- Added device tree overlay source for tinydrm version of the ILI9341 driver
- move pygame initialization to pygame event loop thread as neither pygame nor SDL is
  thread safe and eglMakeCurrent may throw an EGL_BAD_ACCESS exception on pygame.display.blit()
- Updated instructions

2021-08-01 (woelfisch fork)
----------------------------

- last.fm cover art service has been dead for how long? Use MusicBrainz.
- Code cleanup

v1.1.0 (2021-07-29, woelfisch fork)
-----------------------------------

- Require Mopidy v3.2.x and Python 3.7
- Restructure source code to avoid circular imports
- Adjust to current Mopidy Core API
- Port to Python 3 (mainly fix formerly implicit float to int conversions)
- Use Enums god*mmit...
- Search for Artist and Album broken, apparently Mopidy Core issue
- Write directly to framebuffer device
- Add support to automatically return to configurable menu screen
- Make start menu screen configurable
- Add more LIRC / Keyboard actions
- Support evdev (LIRC uinput, gpio-key drivers) devices
- Drop GPIO driver

v1.0.0 (2015-05-26, last 9and3r version)
----------------------------------------

- Require Mopidy v1.0
- Update to work with changed core playback API in Mopidy 1.0
- Search working
- GPIO and Keyboard support
- Resolution factor to adapt the interface for different screen sizes (Thanks to `Syco54645 <https://github.com/Syco54645>`_)
- Background image
- Lower CPU usage (Update screen only when needed)
- Bug Fixes

v0.3.2 (2015-01-09)
-------------------

- Bug Fixes
- UI changes
- Smooth text scrolling
- Search albums, artist or songs (Not fully implemented. Basic functionality)

v0.2.1 (2014-08-02)
-------------------

- Font will be included on installation

v0.2.0 (2014-08-02)
-------------------

- First working version
