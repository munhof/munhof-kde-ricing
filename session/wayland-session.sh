#!/bin/sh
# This file is installed with @RICE_ACCOUNT@ replaced by the dedicated account.
set -eu
if [ "$(id -un)" != '@RICE_ACCOUNT@' ]; then
    echo 'Plasma Rice is restricted to its dedicated test account.' >&2
    exit 1
fi
if [ ! -x /usr/bin/startplasma-wayland ]; then
    echo 'Missing /usr/bin/startplasma-wayland' >&2
    exit 1
fi
export XDG_CURRENT_DESKTOP=KDE
export DESKTOP_SESSION=plasma
export PLASMA_RICE_SESSION=1
if [ -x /usr/lib/plasma-dbus-run-session-if-needed ]; then
    exec /usr/lib/plasma-dbus-run-session-if-needed /usr/bin/startplasma-wayland
fi
exec /usr/bin/startplasma-wayland
