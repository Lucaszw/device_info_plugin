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
import json
import signal
import sys

import paho_mqtt_helpers as pmh

from dmf_device import DmfDevice
from pandas_helpers import PandasJsonEncoder, pandas_object_hook


class DeviceInfoPlugin(pmh.BaseMqttReactor):
    """
    This class is automatically registered with the PluginManager.
    """

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
        self.mqtt_client.publish('microdrop/put/device-model/device',
                                 json.dumps(self.device,
                                            cls=PandasJsonEncoder))

    def __init__(self):
        self.name = self.plugin_name
        self.plugin = None
        self.command_timeout_id = None
        pmh.BaseMqttReactor.__init__(self)
        self._props = {"device": None}
        self.start()

    def on_connect(self, client, userdata, flags, rc):
        self.mqtt_client.subscribe('microdrop/put/device-info-plugin'
                                   '/device')
        self.on_plugin_launch()

    def on_message(self, client, userdata, msg):
        '''
        Callback for when a ``PUBLISH`` message is received from the broker.
        '''
        if msg.topic == 'microdrop/put/device-info-plugin/device':
            self.device = json.loads(msg.payload,
                                     object_hook=pandas_object_hook)
        # TODO: Stop overriding on_message for BaseMqttReactor subscriptions
        if msg.topic == "microdrop/device_info_plugin/exit":
            self.exit()

    def start(self):
        # TODO migrate to pmh.BaseMqttReactor
        # Connect to MQTT broker.
        self._connect()
        # Start loop in background thread.
        signal.signal(signal.SIGINT, self.exit)
        self.mqtt_client.loop_forever()

    def on_disconnect(self, *args, **kwargs):
        # TODO migrate to pmh.BaseMqttReactor
        # Startup Mqtt Loop after disconnected (unless should terminate)
        if self.should_exit:
            sys.exit()
        self._connect()
        self.mqtt_client.loop_forever()


if __name__ == "__main__":
    DeviceInfoPlugin()

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
