#!/bin/sh
# Opens the app full screen on the Touch Display. Started from the desktop session's autostart.
until curl -s -o /dev/null http://localhost:8080/; do sleep 1; done
exec chromium --kiosk --noerrdialogs --disable-infobars --touch-events=enabled --app=http://localhost:8080/
