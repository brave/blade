#!/usr/bin/python3

# Note:   Bluetooth HID Emulator DBUS Service
# Author: Kleomenis Katevas (kkatevas@brave.com)
#         Inspired by: https://gist.github.com/ukBaz/a47e71e7b87fbc851b27cde7d1c0fcf0
# Date:   13/03/2023

import argparse
import os
import socket
import sys

import dbus
import dbus.mainloop.glib
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib


class HumanInterfaceDeviceProfile(dbus.service.Object):
    """
    BlueZ D-Bus Profile for HID
    """

    fd = -1

    @dbus.service.method("org.bluez.Profile1", in_signature="", out_signature="")
    def Release(self):
        mainloop.quit()

    @dbus.service.method("org.bluez.Profile1", in_signature="oha{sv}", out_signature="")
    def NewConnection(self, path, fd, properties):
        self.fd = fd.take()
        print("NewConnection({}, {})".format(path, self.fd))
        for key in properties.keys():
            if key == "Version" or key == "Features":
                print("  {} = 0x{:04x}".format(key, properties[key]))
            else:
                print("  {} = {}".format(key, properties[key]))

    @dbus.service.method("org.bluez.Profile1", in_signature="o", out_signature="")
    def RequestDisconnection(self, path):
        print("RequestDisconnection {}".format(path))

        if self.fd > 0:
            os.close(self.fd)
            self.fd = -1


class BTKbDevice:
    """
    create a bluetooth device to emulate a HID keyboard
    """

    MY_DEV_NAME = "BLaDE"
    # Service port - must match port configured in SDP record
    P_CTRL = 17
    # Service port - must match port configured in SDP record#Interrupt port
    P_INTR = 19
    # BlueZ dbus
    PROFILE_DBUS_PATH = "/bluez/yaptb/btkb_profile"
    ADAPTER_IFACE = "org.bluez.Adapter1"
    DEVICE_INTERFACE = "org.bluez.Device1"
    DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"
    DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"

    # file path of the sdp record to load
    install_dir = os.path.dirname(os.path.realpath(__file__))
    SDP_RECORD_PATH = os.path.join(
        install_dir, "spd_records", "combo_hid_sdp_record.xml"
    )
    # UUID for HID service (1124)
    # https://www.bluetooth.com/specifications/assigned-numbers/service-discovery
    UUID = "00001124-0000-1000-8000-00805f9b34fb"

    def __init__(self, hci=0):
        self.scontrol = None
        self.ccontrol = None  # Socket object for control
        self.sinterrupt = None
        self.cinterrupt = None  # Socket object for interrupt
        self.dev_path = "/org/bluez/hci{}".format(hci)
        self.bus = dbus.SystemBus()
        self.adapter_methods = dbus.Interface(
            self.bus.get_object("org.bluez", self.dev_path), self.ADAPTER_IFACE
        )
        self.adapter_property = dbus.Interface(
            self.bus.get_object(
                "org.bluez", self.dev_path), self.DBUS_PROP_IFACE
        )

        self.bus.add_signal_receiver(
            self.interfaces_added,
            dbus_interface=self.DBUS_OM_IFACE,
            signal_name="InterfacesAdded",
        )

        self.bus.add_signal_receiver(
            self._properties_changed,
            dbus_interface=self.DBUS_PROP_IFACE,
            signal_name="PropertiesChanged",
            arg0=self.DEVICE_INTERFACE,
            path_keyword="path",
        )

        self.config_hid_profile()

        # set the Bluetooth device configuration
        self.alias = BTKbDevice.MY_DEV_NAME
        self.discoverabletimeout = 0
        self.discoverable = True

    def interfaces_added(self, *args, **kwargs):
        pass

    def _properties_changed(self, interface, changed, invalidated, path):
        if self.on_disconnect is not None:
            if "Connected" in changed:
                if not changed["Connected"]:
                    self.on_disconnect()

    def on_disconnect(self):
        mainloop.quit()

    @property
    def address(self):
        """Return the adapter MAC address."""
        return self.adapter_property.Get(self.ADAPTER_IFACE, "Address")

    @property
    def powered(self):
        """
        power state of the Adapter.
        """
        return self.adapter_property.Get(self.ADAPTER_IFACE, "Powered")

    @powered.setter
    def powered(self, new_state):
        self.adapter_property.Set(self.ADAPTER_IFACE, "Powered", new_state)

    @property
    def alias(self):
        return self.adapter_property.Get(self.ADAPTER_IFACE, "Alias")

    @alias.setter
    def alias(self, new_alias):
        self.adapter_property.Set(self.ADAPTER_IFACE, "Alias", new_alias)

    @property
    def discoverabletimeout(self):
        """Discoverable timeout of the Adapter."""
        return self.adapter_props.Get(self.ADAPTER_IFACE, "DiscoverableTimeout")

    @discoverabletimeout.setter
    def discoverabletimeout(self, new_timeout):
        self.adapter_property.Set(
            self.ADAPTER_IFACE, "DiscoverableTimeout", dbus.UInt32(new_timeout)
        )

    @property
    def discoverable(self):
        """Discoverable state of the Adapter."""
        return self.adapter_props.Get(self.ADAPTER_INTERFACE, "Discoverable")

    @discoverable.setter
    def discoverable(self, new_state):
        self.adapter_property.Set(
            self.ADAPTER_IFACE, "Discoverable", new_state)

    def config_hid_profile(self):
        """
        Setup and register HID Profile
        """

        service_record = self.read_sdp_service_record()

        opts = {
            "Role": "client",
            "RequireAuthentication": True,
            "RequireAuthorization": True,
            "AutoConnect": True,
            "ServiceRecord": service_record,
        }

        manager = dbus.Interface(
            self.bus.get_object(
                "org.bluez", "/org/bluez"), "org.bluez.ProfileManager1"
        )

        HumanInterfaceDeviceProfile(self.bus, BTKbDevice.PROFILE_DBUS_PATH)

        manager.RegisterProfile(
            BTKbDevice.PROFILE_DBUS_PATH, BTKbDevice.UUID, opts)

    @staticmethod
    def read_sdp_service_record():
        """
        Read and return SDP record from a file
        :return: (string) SDP record
        """
        try:
            fh = open(BTKbDevice.SDP_RECORD_PATH, "r", encoding="utf-8")
        except OSError:
            sys.exit("Error: Could not open the sdp record.")

        return fh.read()

    def connect(self, address):
        """
        Connect to a paired HID client
        """

        print("Connecting to device with BT Mac address '%s'..." % (str(address)))
        self.scontrol = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
        )
        self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sinterrupt = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
        )
        self.sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.scontrol.connect((address, self.P_CTRL))
        self.sinterrupt.connect((address, self.P_INTR))
        print("Connected!")

    def send(self, msg):
        """
        Send HID message
        :param msg: (bytes) HID packet to send
        """
        self.sinterrupt.send(bytes(bytearray(msg)))


class BTKbService(dbus.service.Object):
    """
    Setup of a D-Bus service to receive HID messages from other
    processes.
    Send the received HID messages to the Bluetooth HID server to send
    """

    def __init__(self, device):

        bus_name = dbus.service.BusName(
            "org.yaptb.btkbservice", bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, "/org/yaptb/btkbservice")

        # create and setup our device
        self.device = BTKbDevice()
        self.device.connect(device)

    @dbus.service.method("org.yaptb.btkbservice", in_signature="ay")
    def send_keys(self, cmd):
        self.device.send(cmd)


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(
        description="Bluetooth HID Emulator DBUS Service.")

    parser.add_argument(
        "-d",
        "--device",
        required=True,
        help="Bluetooth device mac address. Device requires to be paired and authenticated.",
    )

    parsed = parser.parse_args(args)
    return parsed


##################################################################
# MAIN
##################################################################

if __name__ == "__main__":

    # The sockets require root permission
    if not "SUDO_UID" in os.environ:
        sys.exit("Error: Root access is required to run this script. Try with sudo.")

    # parse args
    args = __parse_arguments(sys.argv[1:])

    # run server
    DBusGMainLoop(set_as_default=True)
    service = BTKbService(args.device)
    mainloop = GLib.MainLoop()

    try:
        mainloop.run()
    except SystemExit:
        print("Bluetooth HID Emulator service (bt-connect) was terminated.")
    except KeyboardInterrupt:
        print("Bluetooth HID Emulator service (bt-connect) was interrupted by user.")
