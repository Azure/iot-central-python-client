import pytest
import mock
import time
import configparser
import os
import sys


from azure.iot.device.provisioning.models import RegistrationResult
from azure.iot.device.iothub.models import MethodRequest

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../tests.ini'))

if config['TESTS'].getboolean('Local'):
    sys.path.insert(0, 'src')

from iotc import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents

groupKey = config['TESTS']['GroupKey']
deviceKey = config['TESTS']['DeviceKey']
device_id = config['TESTS']['DeviceId']
scopeId = config['TESTS']['ScopeId']
assignedHub = config['TESTS']['AssignedHub']
expectedHub = config['TESTS']['ExpectedHub']

propPayload = {'prop1': {'value': 40}, '$version': 5}

cmdRequestId = 'abcdef'
cmdName = 'command1'
cmdPayload = 'payload'
methodRequest = MethodRequest(cmdRequestId, cmdName, cmdPayload)


class NewRegState():
    def __init__(self):
        self.assigned_hub = assignedHub

    def assigned_hub(self):
        return self.assigned_hub


class NewProvClient():
    def register(self):
        reg = RegistrationResult('3o375i827i852', 'assigned', NewRegState())
        return reg


class NewDeviceClient():
    def connect(self):
        return True

    def receive_twin_desired_properties_patch(self):
        return propPayload

    def receive_method_request(self):
        return methodRequest

    def send_method_response(self, payload):
        return True

    def patch_twin_reported_properties(self, payload):
        return True


def init(mocker):
    iotc = IoTCClient(device_id, scopeId,
                      IOTCConnectType.IOTC_CONNECT_SYMM_KEY, groupKey)
    mocker.patch('azure.iotcentral.device.client.ProvisioningDeviceClient.create_from_symmetric_key',
                 return_value=NewProvClient())
    mocker.patch('azure.iotcentral.device.client.IoTHubDeviceClient.create_from_connection_string',
                 return_value=NewDeviceClient())
    return iotc


def test_computeKey(mocker):
    iotc = init(mocker)
    assert iotc._compute_derived_symmetric_key(
        groupKey, device_id) == deviceKey


def test_deviceKeyGeneration(mocker):
    iotc = init(mocker)
    iotc.connect()
    assert iotc._key_or_cert == deviceKey


def test_hubConnectionString(mocker):
    iotc = init(mocker)
    iotc.connect()
    assert iotc._hub_conn_string == expectedHub


def test_onproperties_before(mocker):
    on_props = mock.Mock()

    iotc = init(mocker)
    mocker.patch.object(iotc, 'send_property', mock.Mock())
    iotc.on(IOTCEvents.IOTC_PROPERTIES, on_props)
    iotc.connect()
    on_props.assert_called_with('prop1', 40)


def test_onproperties_after(mocker):
    on_props = mock.Mock()

    iotc = init(mocker)
    mocker.patch.object(iotc, 'send_property', mock.Mock())
    iotc.connect()
    iotc.on(IOTCEvents.IOTC_PROPERTIES, on_props)
    # give at least 10 seconds for the new listener to be recognized. assign the listener after connection is discouraged
    time.sleep(11)
    on_props.assert_called_with('prop1', 40)


def test_onCommands_before(mocker):

    on_cmds = mock.Mock()

    def mockedAck():
        print('Callback called')
        return True

    iotc = init(mocker)
    mocker.patch.object(iotc, '_cmd_ack', mockedAck)

    iotc.on(IOTCEvents.IOTC_COMMAND, on_cmds)
    iotc.connect()
    on_cmds.assert_called_with(methodRequest, mockedAck)


def test_onCommands_after(mocker):

    on_cmds = mock.Mock()

    def mockedAck():
        print('Callback called')
        return True

    iotc = init(mocker)
    mocker.patch.object(iotc, '_cmd_ack', mockedAck)

    iotc.connect()
    iotc.on(IOTCEvents.IOTC_COMMAND, on_cmds)

    # give at least 10 seconds for the new listener to be recognized. assign the listener after connection is discouraged
    time.sleep(11)
    on_cmds.assert_called_with(methodRequest, mockedAck)
