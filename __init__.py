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
import json
import logging

import gobject
import paho_mqtt_helpers as pmh

from zmq_plugin.schema import PandasJsonEncoder

from ...app_context import get_app, get_hub_uri
from ...plugin_manager import (IPlugin, PluginGlobals, ScheduleRequest,
                               SingletonPlugin, emit_signal, implements)

logger = logging.getLogger(__name__)

PluginGlobals.push_env('microdrop')


class DeviceInfoPlugin(SingletonPlugin, pmh.BaseMqttReactor):
    """
    This class is automatically registered with the PluginManager.
    """
    implements(IPlugin)
    plugin_name = 'microdrop.device_info_plugin'

    def __init__(self):
        self.name = self.plugin_name
        self.plugin = None
        self.command_timeout_id = None
        pmh.BaseMqttReactor.__init__(self)
        self.start()

    def on_connect(self, client, userdata, flags, rc):
        self.mqtt_client.subscribe('microdrop/dmf-device-ui/get-device')

    def on_message(self, client, userdata, msg):
        '''
        Callback for when a ``PUBLISH`` message is received from the broker.
        '''
        logger.info('[on_message] %s: "%s"', msg.topic, msg.payload)
        if msg.topic == 'microdrop/dmf-device-ui/get-device':
            self.get_device()

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
        app = get_app()
        if app.dmf_device:
            # XXX: retain DmfDevice for web-ui reload
            data = json.dumps(app.dmf_device, cls=PandasJsonEncoder)
            self.mqtt_client.publish('microdrop/device-info-plugin/'
                                      'device-swapped', data, retain=True)
        self.get_device()

    def get_device(self):
        app = get_app()

        if app.dmf_device:
            data = {}
            data['name'] = app.dmf_device.name
            data['svg_filepath'] = app.dmf_device.svg_filepath
            data['electrode_channels'] = app.dmf_device.get_electrode_channels().to_json()
            data['electrode_areas'] = app.dmf_device.get_electrode_areas().to_json()
            data['bounding_box'] = app.dmf_device.get_bounding_box()
            data['max_channel'] = app.dmf_device.max_channel()
            # data['svg'] = app.dmf_device.to_svg()
            data['diff_electrode_channels'] = app.dmf_device.diff_electrode_channels().to_json()
            self.mqtt_client.publish('microdrop/device-info-plugin/get-device',
                                      json.dumps(data))
        else:
            self.mqtt_client.publish('microdrop/device-info-plugin/get-device',
                                      json.dumps(None))

        return app.dmf_device

    def get_schedule_requests(self, function_name):
        """
        Returns a list of scheduling requests (i.e., ScheduleRequest instances)
        for the function specified by function_name.
        """
        if function_name == 'on_dmf_device_swapped':
            return [ScheduleRequest('microdrop.app', self.name)]
        return []


PluginGlobals.pop_env()
