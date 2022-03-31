BEGIN {
  print "# SDL2 Scancodes, generated from";
  print "# https://github.com/libsdl-org/SDL/blob/main/include/SDL_scancode.h"
  print "# "
  print "# These are not quite the same as the USB HID Usage codes documented at";
  print "# https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf";
  print
}

$1 ~ /^\s*SDL_SCANCODE/ {
  sub(/SDL_SCANCODE/, "SC", $1);
  sub(/,/, "", $3);
  print $1 "=" $3
}
