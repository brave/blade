#!/bin/bash

# Note:   Setup the controller for BLaDE
# Author: Kleomenis Katevas (kkatevas@brave.com)
#         (original code from Matteo Varvello at Brave Software)
# Date:   17/02/2023

change_config() {
  sudo sed -i "s/\(^$1 *= *\).*/\1$2/" $3
}

setup_service() {
  local config_file=$1
  local service_name=$2
  local target_path="/lib/systemd/system/${service_name}"

  sudo cp "${config_file}" "${target_path}"
  sudo chmod 644 "${target_path}"
  sudo systemctl daemon-reload
  sudo systemctl enable "${service_name}"
}

# update package list
sudo apt update
sudo apt upgrade -y
sudo apt autoremove -y

# install required packages
sudo apt install -y git tmux vim  # generic
sudo apt install -y python3-pip  # custom python packages
sudo apt install -y python3-numpy python3-pandas python3-numba python3-matplotlib python3-seaborn python3-tqdm python3-coloredlogs  # data analysis
sudo apt install -y android-tools-adb android-tools-fastboot  # android
sudo apt install -y usbmuxd libimobiledevice6 libimobiledevice-utils ideviceinstaller ifuse  # ios
sudo apt install -y python3-dbus python3-smbus
sudo apt install -y expect tcl tcllib  # automate interactive scripts
sudo apt install -y python3-flask  # rest server

# install Node.js 20.x (LTS) from https://deb.nodesource.com
sudo apt install -y ca-certificates curl gnupg
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
NODE_MAJOR=20
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | sudo tee /etc/apt/sources.list.d/nodesource.list
sudo apt-get update && sudo apt install nodejs -y

# used for mounting ios devices
mkdir ~/ios-mount

# tmux conf
sudo cp configs/tmux.conf $HOME/.tmux.conf

# key generation
ssh-keygen -t rsa -N "" -f $HOME/.ssh/id_rsa

# USB power controlling
# ykush (https://github.com/Yepkit/ykush)
sudo apt install -y libusb-1.0-0 libusb-1.0-0-dev
if [ ! -d "ykush" ]
then
    git clone https://github.com/Yepkit/ykush
fi
cd ykush
./build.sh
sudo ./install.sh
cd ..
# pykush (https://github.com/Yepkit/pykush)
if [ ! -d "pykush" ]
then
    git clone https://github.com/Yepkit/pykush
fi
cd pykush
sudo python setup.py install
cd ..

# Monsoon Power Monitor (https://github.com/msoon/PyMonsoon)
sudo apt install -y python3-scipy
sudo pip install Monsoon --break-system-packages

# Bluetooth Control support
pip install readchar --break-system-packages
sudo service bluetooth stop
change_config ExecStart "/usr/libexec/bluetooth/bluetoothd -P input" /lib/systemd/system/bluetooth.service
sudo cp configs/org.yaptb.btkbservice.conf /etc/dbus-1/system.d
sudo bash -c 'PRETTY_HOSTNAME=BLaDE > /etc/machine-info'
sudo systemctl daemon-reload
sudo service bluetooth start

# Tranco list
pip install tranco --break-system-packages

# Setup services
setup_service "configs/switch-voltage-init.service" "blade-switch-voltage-init.service"
setup_service "configs/control-monsoon-init.service" "blade-control-monsoon-init.service"
setup_service "configs/fix-bt.service" "blade-fix-bt.service"

# make tools available in path as executables
sudo chmod +x $HOME/blade/src/tools/*.py
sudo chmod +x $HOME/blade/src/tools/*.sh
echo "" >> $HOME/.bashrc
echo "# Custom Paths" >> $HOME/.bashrc
echo "export PATH=\"~/blade/src/tools:$PATH\"" >> $HOME/.bashrc
source $HOME/.bashrc

# soft symbolic links needed for 'sudo' execution
sudo ln -s $HOME/blade/src/tools/bt-connect.py /bin/bt-connect

# allow USB access for all users
echo 'SUBSYSTEM=="usb", MODE="0666"' | sudo tee /etc/udev/rules.d/usb.rules > /dev/null

# install scrcpy (Android mirroring). Updated version than the one in apt.
hash scrcpy > /dev/null 2>&1
if [ $? -eq 1 ]
then
	# get the code 
	git clone https://github.com/Genymobile/scrcpy
	
	# runtime dependencies
	sudo apt install -y ffmpeg

	# client build dependencies
    sudo apt install -y ffmpeg libsdl2-2.0-0 \
                 make gcc pkg-config meson ninja-build libsdl2-dev \
                 libavcodec-dev libavdevice-dev libavformat-dev libavutil-dev \
                 libswresample-dev libusb-1.0-0 libusb-1.0-0-dev
	
	# compile prebuild 
	cd scrcpy
	./install_release.sh
    cd ..
else 
	echo "scrcpy (Android mirroring) already installed. Nothing to do"
fi

# install novnc
sudo apt install -y novnc

# install tigervnc and cp xstartup file
sudo apt install -y tigervnc-standalone-server
mkdir -p $HOME"/.vnc"
cp ./configs/xstartup $HOME"/.vnc"

# rebooting the device for all configuration to take effect
echo "Rebooting..."
sudo reboot
