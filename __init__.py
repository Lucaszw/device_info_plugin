"""
Copyright 2015 Christian Fobel

This file is part of device_info_plugin.

device_info_plugin is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

dmf_control_board is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with device_info_plugin.  If not, see <http://www.gnu.org/licenses/>.
"""
import io

import paho_mqtt_helpers as pmh
from dmf_device import DmfDevice


class DeviceInfoPlugin(pmh.BaseMqttReactor):
    """
    This class is automatically registered with the PluginManager.
    """

    def __init__(self):
        self.name = self.plugin_name
        self.plugin = None
        self.command_timeout_id = None
        pmh.BaseMqttReactor.__init__(self)
        self._props = {"device": None}
        self.start()

    @property
    def device(self):
        return self._props["device"]

    @device.setter
    def device(self, value):
        name = value["name"]
        data = value["file"]

        # Initialize DMF Device:
        fileobj = io.BytesIO(str(data))
        device = DmfDevice.load(fileobj, name=name)
        device.svg_filepath = name
        self._props["device"] = device

        # Publish Device Object:
        self.trigger("put-device", self.device)

    def on_put_device(self, payload, args):
        self.device = payload

    def onRunningStateRequested(self, payload, args):
        self.trigger("send-running-state", self.plugin_path)

    def listen(self):
        self.onPutMsg("device", self.on_put_device)
        self.bindPutMsg("device-model", "device", "put-device")

        # TODO: Create MicrodropPlugin base class (that inherits from paho)
        self.onSignalMsg("web-server", "running-state-requested",
                         self.onRunningStateRequested)
        self.bindSignalMsg("running", "send-running-state")


if __name__ == "__main__":
    DeviceInfoPlugin()
