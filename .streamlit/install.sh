#!/bin/bash

echo "Updating apt-get..."
sudo apt-get update -y

echo "Removing existing chromium if present..."
sudo apt-get remove chromium -y
sudo apt-get autoremove -y

echo "Installing common Chrome dependencies..."
sudo apt-get install -y libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1

echo "Installing Google Chrome..."
wget -v https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/google-chrome-stable_current_amd64.deb
ls -l /tmp/google-chrome-stable_current_amd64.deb # Verify download
sudo apt install /tmp/google-chrome-stable_current_amd64.deb -y
sudo rm /tmp/google-chrome-stable_current_amd64.deb
echo "Google Chrome installed."
which google-chrome # Verify installation path
google-chrome --version # Verify Chrome version

# Create a symlink for google-chrome in /usr/local/bin
sudo ln -s /usr/bin/google-chrome /usr/local/bin/google-chrome
echo "Symlink for google-chrome created at /usr/local/bin/google-chrome."
ls -l /usr/local/bin/google-chrome # Verify symlink

# Install chromedriver
# Get the installed Chrome version
INSTALLED_CHROME_VERSION=$(google-chrome --version | grep -Eo "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" | head -n 1)
echo "Detected installed Chrome version: $INSTALLED_CHROME_VERSION"

# Get the latest compatible ChromeDriver version for the installed Chrome version
CHROMEDRIVER_VERSION=$(wget -qO- "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_$INSTALLED_CHROME_VERSION")
echo "Downloading ChromeDriver version: $CHROMEDRIVER_VERSION"

wget -q --continue -P /tmp "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROMEDRIVER_VERSION/linux64/chromedriver-linux64.zip"
unzip /tmp/chromedriver-linux64.zip -d /tmp

# Move chromedriver to /usr/local/bin and set permissions
sudo mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver
echo "ChromeDriver installed at /usr/local/bin/chromedriver."
ls -l /usr/local/bin/chromedriver # Verify chromedriver existence and permissions

# Check PATH environment variable
echo "PATH: $PATH"
