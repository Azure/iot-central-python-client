import pytest
import mock
import time
import asyncio
import configparser
import os
import sys

from contextlib import suppress

from azure.iot.device.provisioning.models import RegistrationResult
from azure.iot.device.iothub.models import MethodRequest,Message


config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../tests.ini'))

if config['TESTS'].getboolean('Local'):
    sys.path.insert(0, 'src')

from iotc import IOTCConnectType, IOTCLogLevel, IOTCEvents
from iotc.aio import IoTCClient

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
        self.assigned_hub = assignedHub

    def assigned_hub(self):
        return self.assigned_hub


class NewProvClient():
    async def register(self):
        reg = RegistrationResult('3o375i827i852', 'assigned', NewRegState())
        return reg


class NewDeviceClient():
    async def connect(self):
        return True

    async def receive_twin_desired_properties_patch(self):
        await asyncio.sleep(3)
        return propPayload

    async def receive_method_request(self):
        await asyncio.sleep(3)
        return methodRequest

    async def receive_message(self):
        await asyncio.sleep(3)
        return enqueued_message

    async def send_method_response(self, payload):
        return True

    async def patch_twin_reported_properties(self, payload):
        return True


def async_return(result):
    f = asyncio.Future()
    f.set_result(result)
    return f


async def stop_threads(client):
    client._prop_thread.cancel()
    client._cmd_thread.cancel()
    client._enqueued_cmd_thread.cancel()


@pytest.mark.asyncio
def init(mocker):
    client = IoTCClient(device_id, scopeId,
                      IOTCConnectType.IOTC_CONNECT_SYMM_KEY, groupKey)
    mocker.patch('iotc.aio.ProvisioningDeviceClient.create_from_symmetric_key',
                 return_value=NewProvClient())
    mocker.patch('iotc.aio.IoTHubDeviceClient.create_from_connection_string',
                 return_value=NewDeviceClient())
    return client


@pytest.mark.asyncio
async def test_computeKey(mocker):
    client = init(mocker)
    key = await client._compute_derived_symmetric_key(
        groupKey, device_id)
    assert key == deviceKey


@pytest.mark.asyncio
async def test_deviceKeyGeneration(mocker):
    client = init(mocker)
    await client.connect()
    assert client._key_or_cert == deviceKey
    await stop_threads(client)


@pytest.mark.asyncio
async def test_hubConnectionString(mocker):
    client = init(mocker)
    await client.connect()
    assert client._hub_conn_string == expectedHub
    await stop_threads(client)


@pytest.mark.asyncio
async def test_onproperties_before(mocker):
    client = init(mocker)

    async def onProps(propname, propvalue):
        assert propname == 'prop1'
        assert propvalue == 40
        await stop_threads(client)

    mocker.patch.object(client, 'send_property', return_value=True)
    client.on(IOTCEvents.IOTC_PROPERTIES, onProps)
    await client.connect()
    try:
        await client._prop_thread
        await client._cmd_thread
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_onproperties_after(mocker):
    client = init(mocker)

    async def onProps(propname, propvalue):
        assert propname == 'prop1'
        assert propvalue == 40
        await stop_threads(client)
        return True

    mocker.patch.object(client, 'send_property', return_value=True)
    await client.connect()
    client.on(IOTCEvents.IOTC_PROPERTIES, onProps)

    try:
        await client._prop_thread
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_on_commands_before(mocker):

    client = init(mocker)

    async def onCmds(command, ack):
        ret = ack()
        assert ret == 'mocked'
        await stop_threads(client)
        return True

    def mockedAck():
        return 'mocked'

    mocker.patch.object(client, '_cmd_ack', mockedAck)

    client.on(IOTCEvents.IOTC_COMMAND, onCmds)
    await client.connect()
    try:
        await client._cmd_thread
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_on_commands_after(mocker):

    client = init(mocker)

    async def onCmds(command, ack):
        ret = ack()
        assert ret == 'mocked'
        await stop_threads(client)
        return True

    def mockedAck():
        return 'mocked'

    mocker.patch.object(client, '_cmd_ack', mockedAck)

    await client.connect()
    client.on(IOTCEvents.IOTC_COMMAND, onCmds)

    try:
        await client._cmd_thread
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_on_enqueued_commands_before(mocker):

    client = init(mocker)

    async def on_enqs(command_name,command_data):
        assert command_name == enqueued_method_name.split(':')[1]
        await stop_threads(client)
        return True


    client.on(IOTCEvents.IOTC_ENQUEUED_COMMAND, on_enqs)
    await client.connect()
    try:
        await client._enqueued_cmd_thread
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_on_enqueued_commands_after(mocker):

    client = init(mocker)

    async def on_enqs(command_name,command_data):
        assert command_name == enqueued_method_name.split(':')[1]
        await stop_threads(client)
        return True


    await client.connect()
    client.on(IOTCEvents.IOTC_ENQUEUED_COMMAND, on_enqs)
    try:
        await client._enqueued_cmd_thread
    except asyncio.CancelledError:
        pass
