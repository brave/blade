#!/bin/bash

vncserver -kill :1
killall -q websockify 2>/dev/null
killall -q scrcpy 2>/dev/null
