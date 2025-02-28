#!/bin/bash

# Note:   Update BLaDE-Pi and all installed packages
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   09/02/2025

# Update the system and all installed packages
sudo apt update && sudo apt dist-upgrade -y
sudo apt autoremove -y

# Update pipx installed packages
pipx upgrade-all
