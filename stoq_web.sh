#!/bin/bash

# laucher-geometry em .stoq/settings
# openssl passwd -1  > ~/.config/broadway.passwd

GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 bin/stoq
