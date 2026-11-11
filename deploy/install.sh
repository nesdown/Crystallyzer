#!/bin/sh
# Sets up Crystallyzer on Raspberry Pi OS (Bookworm or newer). Run from the repository folder.
set -e

echo "Installing system packages"
sudo apt-get update
sudo apt-get install -y python3-venv python3-picamera2 python3-numpy chromium curl

echo "Creating the Python environment, with access to the system camera library"
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e ".[pi]"

echo "Turning on I2C, 1-Wire and the cameras"
CONFIG=/boot/firmware/config.txt
for line in "dtparam=i2c_arm=on" "dtoverlay=w1-gpio,gpiopin=4" "camera_auto_detect=1"; do
  grep -qx "$line" "$CONFIG" || echo "$line" | sudo tee -a "$CONFIG" >/dev/null
done

echo "Starting the app at boot"
sudo cp deploy/crystallyzer.service /etc/systemd/system/
sudo sed -i "s#/home/pi/crystallyzer#$(pwd)#g; s#User=pi#User=$(whoami)#" /etc/systemd/system/crystallyzer.service
sudo systemctl enable --now crystallyzer

mkdir -p ~/.config/autostart
cat > ~/.config/autostart/crystallyzer.desktop <<DESKTOP
[Desktop Entry]
Type=Application
Name=Crystallyzer
Exec=sh $(pwd)/deploy/kiosk.sh
DESKTOP

echo "Done. Reboot, then run: .venv/bin/crystallyzer check"
