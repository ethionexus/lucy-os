# Lucy OS live wallpaper

Place `lucy-wallpaper-live.mp4` here. The Lucy OS Live Wallpaper
Service (`lucy-wallpaper.service`) loops it as the desktop background
on X11 sessions.

The engine (`/usr/local/bin/lucy-wallpaper`) uses `xwinwrap` + `mpv`
when `xwinwrap` is available (install it from the AUR for a clean,
override-redirect background beneath the desktop icons). Without
`xwinwrap`, it falls back to an `mpv` desktop-window, and to the
static Openbox wallpaper when the video is not present.
