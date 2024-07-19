#!/bin/bash

dir="/sys/kernel/debug"
sudo chmod 777 $dir

conn_min_interval=$dir"/bluetooth/hci0/conn_min_interval"
conn_max_interval=$dir"/bluetooth/hci0/conn_max_interval"
supervision_timeout=$dir"/bluetooth/hci0/supervision_timeout"
adv_min_interval=$dir"/bluetooth/hci0/adv_min_interval"
adv_max_interval=$dir"/bluetooth/hci0/adv_max_interval"

sudo chmod 777 $conn_min_interval
sudo chmod 777 $conn_max_interval
sudo chmod 777 $supervision_timeout
sudo chmod 777 $adv_min_interval
sudo chmod 777 $adv_max_interval

sudo echo 15 > $conn_min_interval
sudo echo 30 > $conn_max_interval
sudo echo 2000 > $supervision_timeout
sudo echo 153 > $adv_min_interval
sudo echo 153 > $adv_max_interval
