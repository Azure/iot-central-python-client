import pytest
import mock
import time
import configparser
import os
import sys


from azure.iot.device.iothub.models import MethodRequest,Message

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../tests.ini'))

if config['TESTS'].getboolean('Local'):
    sys.path.insert(0, 'src')

from iotc import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents

try:
    groupKey = config['TESTS']['GroupKey']
except:
    groupKey='groupKey'

try:
    deviceKey = config['TESTS']['DeviceKey']
except:
    deviceKey='kPufjjN/EMoyKcNiAXvlTz8H61mlhSnmvoF6dxhnysA='

try:
    device_id = config['TESTS']['DeviceId']
except:
    device_id='device_id'

try:
    scopeId = config['TESTS']['ScopeId']
except:
    scopeId='scopeId'

try:
    assignedHub = config['TESTS']['AssignedHub']
except:
    assignedHub='assignedHub'

try:
    expectedHub = config['TESTS']['ExpectedHub']
except:
    expectedHub='HostName=assignedHub;DeviceId=device_id;SharedAccessKey=kPufjjN/EMoyKcNiAXvlTz8H61mlhSnmvoF6dxhnysA='


propPayload = {'prop1': {'value': 40}, '$version': 5}

cmdRequestId = 'abcdef'
cmdName = 'command1'
cmdPayload = 'payload'
methodRequest = MethodRequest(cmdRequestId, cmdName, cmdPayload)

enqueued_method_name='test:enqueued'

enqueued_message = Message('test_enqueued')
enqueued_message.custom_properties['method-name']=enqueued_method_name

class NewRegState():
    def __init__(self):
        self._assigned_hub = assignedHub

    def get_assigned_hub(self):
        return self._assigned_hub
    
    assigned_hub=property(get_assigned_hub)

class NewRegResult():
    def __init__(self):
        self._registration_state=NewRegState()
    
    def get_registration_state(self):
        return self._registration_state

    registration_state=property(get_registration_state)


class NewProvClient():
    def register(self):
        return NewRegResult()


class NewDeviceClient():
    def connect(self):
        return True

    def receive_twin_desired_properties_patch(self):
        return propPayload

    def receive_method_request(self):
        return methodRequest
    
    def receive_message(self):
        return enqueued_message


    def send_method_response(self, payload):
        return True

    def patch_twin_reported_properties(self, payload):
        return True

    def get_twin(self):
        return 'Twin'


def init(mocker):
    client = IoTCClient(device_id, scopeId,
                      IOTCConnectType.IOTC_CONNECT_SYMM_KEY, groupKey)
    mocker.patch('iotc.ProvisioningDeviceClient.create_from_symmetric_key',
                 return_value=NewProvClient())
    mocker.patch('iotc.IoTHubDeviceClient.create_from_connection_string',
                 return_value=NewDeviceClient())
    return client


def test_computeKey(mocker):
    client = init(mocker)
    assert client._compute_derived_symmetric_key(
        groupKey, device_id) == deviceKey


def test_deviceKeyGeneration(mocker):
    client = init(mocker)
    client.connect()
    assert client._key_or_cert == deviceKey


def test_hubConnectionString(mocker):
    client = init(mocker)
    client.connect()
    assert client._hub_conn_string == expectedHub


def test_onproperties_before(mocker):
    on_props = mock.Mock()

    client = init(mocker)
    mocker.patch.object(client, 'send_property', mock.Mock())
    client.on(IOTCEvents.IOTC_PROPERTIES, on_props)
    client.connect()
    on_props.assert_called_with('prop1', 40,None)


def test_onproperties_after(mocker):
    on_props = mock.Mock()

    client = init(mocker)
    mocker.patch.object(client, 'send_property', mock.Mock())
    client.connect()
    client.on(IOTCEvents.IOTC_PROPERTIES, on_props)
    # give at least 10 seconds for the new listener to be recognized. assign the listener after connection is discouraged
    time.sleep(11)
    on_props.assert_called_with('prop1', 40,None)


def test_onCommands_before(mocker):

    on_cmds = mock.Mock()

    def mockedAck():
        print('Callback called')
        return True

    client = init(mocker)
    mocker.patch.object(client, '_cmd_ack', mockedAck)

    client.on(IOTCEvents.IOTC_COMMAND, on_cmds)
    client.connect()
    on_cmds.assert_called_with(methodRequest, mockedAck)


def test_onCommands_after(mocker):

    on_cmds = mock.Mock()

    def mockedAck():
        print('Callback called')
        return True

    client = init(mocker)
    mocker.patch.object(client, '_cmd_ack', mockedAck)

    client.connect()
    client.on(IOTCEvents.IOTC_COMMAND, on_cmds)

    # give at least 10 seconds for the new listener to be recognized. assign the listener after connection is discouraged
    time.sleep(11)
    on_cmds.assert_called_with(methodRequest, mockedAck)


def test_on_enqueued_commands_before(mocker):

    def on_enqs(command_name,command_data):
        assert command_name == enqueued_method_name.split(':')[1]
        return True

    client = init(mocker)
    client.on(IOTCEvents.IOTC_ENQUEUED_COMMAND, on_enqs)
    client.connect()


def test_on_enqueued_commands_after(mocker):

    def on_enqs(command_name,command_data):
        assert command_name == enqueued_method_name.split(':')[1]
        return True

    client = init(mocker)

    client.connect()
    client.on(IOTCEvents.IOTC_ENQUEUED_COMMAND, on_enqs)

    # give at least 10 seconds for the new listener to be recognized. assign the listener after connection is discouraged
    time.sleep(11)
