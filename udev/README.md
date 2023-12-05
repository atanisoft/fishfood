# Custom udev rules for Fishfood boards

The 99-fishfood.rules file can optionally be copied to /etc/udev/rules.d to provide
constant names for both Starfish and Jellyfish boards based on VID/PID matching.

If you are using a group other than "usb" for access to USB devices by users other
than root be sure to adjust the group name reference accordingly.