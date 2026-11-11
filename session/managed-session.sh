#!/bin/sh
# Run as the actual SDDM-selected user, NOT as root.
set -eu
if [ "$#" -ne 1 ]; then echo "Profile required" >&2; exit 2; fi
profile="$1"
case "$profile" in
    original|rice) ;;
    *) echo "Invalid Plasma profile: $profile" >&2; exit 2 ;;
esac
/usr/bin/python3 /usr/local/libexec/munhof-plasma-rice-profilectl activate "$profile" || exit 2
export XDG_CURRENT_DESKTOP=KDE
export DESKTOP_SESSION=plasma
export XDG_SESSION_DESKTOP=KDE
export PLASMA_RICE_PROFILE="$profile"
if [ -x /usr/lib/plasma-dbus-run-session-if-needed ]; then
    exec /usr/lib/plasma-dbus-run-session-if-needed /usr/bin/startplasma-wayland
fi
exec /usr/bin/startplasma-wayland
