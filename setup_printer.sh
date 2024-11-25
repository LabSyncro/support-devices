#!/bin/bash

set -e # Exit immediately if any command failed

echo "Updating system ..."
sudo apt update && sudo apt update -y

echo "Installing pre-requisite ..."
sudo apt install wget
sudo apt install -y cups wget dpkg
sudo apt install cups-bsd

echo "Adding pi user to lpadmin group ..."\
sudo usermod -a -G lpadmin pi

echo "Instlaling the printer driver ..."
# Navigate to current folder
sudo dpkg -i XP_365B.deb || sudo apt --fix-broken install -y

echo "Installing image processor ..."
pip install Pillow
