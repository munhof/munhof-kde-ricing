# Compatibility policy

Target: Garuda Linux, KDE Plasma 6, Wayland and AMD Radeon. Runtime validation on the user's actual laptop is pending.

The Python tests execute without a graphical session; they do not establish that KWin scripts or graphical effects behave correctly.

Polonium must be installed separately: https://github.com/zeroxoneafour/polonium

KScreen, PowerDevil, SDDM, iio-sensor-proxy, touchscreen and tablet orientation are deliberately outside the v0.1 managed scope.
