#!/bin/bash

echo "Updating apt-get..."
sudo apt-get update -y

echo "Removing existing chromium if present..."
sudo apt-get remove chromium -y
sudo apt-get autoremove -y

echo "Installing Google Chrome..."
wget -v https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/google-chrome-stable_current_amd64.deb
ls -l /tmp/google-chrome-stable_current_amd64.deb # Verify download
sudo apt install /tmp/google-chrome-stable_current_amd64.deb -y
sudo rm /tmp/google-chrome-stable_current_amd64.deb
echo "Google Chrome installed."
which google-chrome # Verify installation path
google-chrome --version # Verify Chrome version

# Install chromedriver
# Get the installed Chrome version
INSTALLED_CHROME_VERSION=$(google-chrome --version | grep -Eo "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" | head -n 1)
echo "Detected installed Chrome version: $INSTALLED_CHROME_VERSION"

# Get the latest compatible ChromeDriver version for the installed Chrome version
CHROMEDRIVER_VERSION=$(wget -qO- "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_$INSTALLED_CHROME_VERSION")
echo "Downloading ChromeDriver version: $CHROMEDRIVER_VERSION"

wget -q --continue -P /tmp "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROMEDRIVER_VERSION/linux64/chromedriver-linux64.zip"
unzip /tmp/chromedriver-linux64.zip -d /tmp

# Move chromedriver to /app and set permissions
mkdir -p /app
sudo mv /tmp/chromedriver-linux64/chromedriver /app/chromedriver
sudo chmod +x /app/chromedriver
echo "ChromeDriver installed at /app/chromedriver."
ls -l /app/chromedriver # Verify chromedriver existence and permissions

# Add /app to PATH
export PATH="/app:$PATH"
echo "PATH updated: $PATH" # Check PATH environment variable
