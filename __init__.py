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
import cPickle as pickle
import itertools
import io
import json
import logging
from lxml import etree

import gobject
import paho_mqtt_helpers as pmh

from dmf_device  import DmfDevice
from svg_model import (INKSCAPE_NSMAP, svg_shapes_to_df, INKSCAPE_PPmm,
                       compute_shape_centers)
from zmq_plugin.schema import PandasJsonEncoder, pandas_object_hook


from ...app_context import get_app, get_hub_uri
from ...plugin_manager import (IPlugin, PluginGlobals, ScheduleRequest,
                               SingletonPlugin, emit_signal, implements)

logger = logging.getLogger(__name__)

PluginGlobals.push_env('microdrop')

ELECTRODES_XPATH = (r'//svg:g[@inkscape:label="Device"]//svg:path | '
                    r'//svg:g[@inkscape:label="Device"]//svg:polygon')

class DeviceInfoPlugin(SingletonPlugin, pmh.BaseMqttReactor):
    """
    This class is automatically registered with the PluginManager.
    """
    implements(IPlugin)
    plugin_name = 'microdrop.device_info_plugin'

    @property
    def device(self):
        return self._props["device"]

    @device.setter
    def device(self, value):
        name = value["name"]
        data = value["file"]

        # Initialize DMF Device:
        fileobj = io.BytesIO(str(data))
        device = DmfDevice.load(fileobj,name=name)
        device.svg_filepath = name
        self._props["device"] = device

        # Publish Device Object:
        # self.mqtt_client.publish('microdrop/device-info-plugin/state/device',
        #                          json.dumps(self.device,cls=PandasJsonEncoder),
        #                          retain=False)
        self.mqtt_client.publish('microdrop/state/device',
                                 json.dumps(self.device,cls=PandasJsonEncoder),
                                 retain=True)
    def __init__(self):
        self.name = self.plugin_name
        self.plugin = None
        self.command_timeout_id = None
        pmh.BaseMqttReactor.__init__(self)
        self._props = {"device": None}
        self.start()

    def on_connect(self, client, userdata, flags, rc):
        self.mqtt_client.subscribe('microdrop/put/device-info-plugin/state/device')

    def on_message(self, client, userdata, msg):
        '''
        Callback for when a ``PUBLISH`` message is received from the broker.
        '''
        # logger.info('[on_message] %s: "%s"', msg.topic, msg.payload)
        if msg.topic == 'microdrop/put/device-info-plugin/state/device':
            self.device = json.loads(msg.payload, object_hook=pandas_object_hook)

    def on_plugin_enable(self):
        """
        Handler called once the plugin instance is enabled.

        Note: if you inherit your plugin from AppDataController and don't
        implement this handler, by default, it will automatically load all
        app options from the config file. If you decide to overide the
        default handler, you should call:

            AppDataController.on_plugin_enable(self)

        to retain this functionality.
        """
        pass

    def on_plugin_disable(self):
        """
        Handler called once the plugin instance is disabled.
        """
        pass

    def on_app_exit(self):
        """
        Handler called just before the MicroDrop application exits.
        """
        pass

    def on_dmf_device_swapped(self, old_device, new_device):
        # Notify other plugins that device has been swapped.
        if self.device:
            # XXX: retain DmfDevice for web-ui reload
            data = json.dumps(self.device, cls=PandasJsonEncoder)
            self.mqtt_client.publish('microdrop/device-info-plugin/'
                                      'device-swapped', data, retain=False)
        self.get_device()

    def get_device(self):

        if self.device:
            data = {}
            data['name'] = self.device.name
            data['electrode_channels'] = self.device.get_electrode_channels().to_json()
            data['electrode_areas'] = self.device.get_electrode_areas().to_json()
            data['bounding_box'] = self.device.get_bounding_box()
            data['max_channel'] = self.device.max_channel()
            data['diff_electrode_channels'] = self.device.diff_electrode_channels().to_json()
            self.mqtt_client.publish('microdrop/device-info-plugin/get-device',
                                      json.dumps(data))
        else:
            self.mqtt_client.publish('microdrop/device-info-plugin/get-device',
                                      json.dumps(None))

        return self.device

    def get_schedule_requests(self, function_name):
        """
        Returns a list of scheduling requests (i.e., ScheduleRequest instances)
        for the function specified by function_name.
        """
        if function_name == 'on_dmf_device_swapped':
            return [ScheduleRequest('microdrop.app', self.name)]
        return []


PluginGlobals.pop_env()
