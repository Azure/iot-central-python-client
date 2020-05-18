import pytest
import mock
import time
import asyncio
import configparser
import os

from contextlib import suppress

from azure.iot.device.provisioning.models import RegistrationResult
from azure.iot.device.iothub.models import MethodRequest

from azure.iotcentral.device.client.aio import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__),'../tests.ini'))

groupKey=config['TESTS']['GroupKey']
deviceKey=config['TESTS']['DeviceKey']
device_id=config['TESTS']['DeviceId']
scopeId=config['TESTS']['ScopeId']
assignedHub=config['TESTS']['AssignedHub']
expectedHub=config['TESTS']['ExpectedHub']

propPayload={'prop1':{'value':40},'$version':5}

cmdRequestId='abcdef'
cmdName='command1'
cmdPayload='payload'
methodRequest=MethodRequest(cmdRequestId,cmdName,cmdPayload)



class NewRegState():
  def __init__(self):
    self.assigned_hub=assignedHub
  
  def assigned_hub(self):
    return self.assigned_hub

class NewProvClient():
  async def register(self):
      reg=RegistrationResult('3o375i827i852','assigned',NewRegState())
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

  async def send_method_response(self,payload):
    return True
  
  async def patch_twin_reported_properties(self,payload):
    return True

def async_return(result):
    f = asyncio.Future()
    f.set_result(result)
    return f


async def stop_threads(iotc):
  iotc._prop_thread.cancel()
  iotc._cmd_thread.cancel()
  
  
@pytest.mark.asyncio
def init(mocker):
  iotc=IoTCClient(device_id, scopeId,
                  IOTCConnectType.IOTC_CONNECT_SYMM_KEY, groupKey)
  mocker.patch('azure.iotcentral.device.client.aio.ProvisioningDeviceClient.create_from_symmetric_key',return_value=NewProvClient())
  mocker.patch('azure.iotcentral.device.client.aio.IoTHubDeviceClient.create_from_connection_string',return_value=NewDeviceClient())
  return iotc



@pytest.mark.asyncio
async def test_computeKey(mocker):
  iotc=init(mocker)
  assert iotc._compute_derived_symmetric_key(groupKey,device_id) == deviceKey

@pytest.mark.asyncio
async def test_deviceKeyGeneration(mocker):
  iotc = init(mocker)
  await iotc.connect()
  assert iotc._key_or_cert == deviceKey
  await stop_threads(iotc)


@pytest.mark.asyncio
async def test_hubConnectionString(mocker):
  iotc = init(mocker)
  await iotc.connect()
  assert iotc._hub_conn_string == expectedHub
  await stop_threads(iotc)


@pytest.mark.asyncio
async def test_onproperties_before(mocker):
  iotc = init(mocker)

  async def onProps(propname,propvalue):
    assert propname == 'prop1'
    assert propvalue == 40
    await stop_threads(iotc)

  mocker.patch.object(iotc,'send_property',return_value=True)
  iotc.on(IOTCEvents.IOTC_PROPERTIES,onProps)
  await iotc.connect()
  try:
    await iotc._prop_thread
    await iotc._cmd_thread
  except asyncio.CancelledError:
    pass
 


@pytest.mark.asyncio
async def test_onproperties_after(mocker):
  iotc = init(mocker)
  
  async def onProps(propname,propvalue):
    assert propname == 'prop1'
    assert propvalue == 40
    await stop_threads(iotc)
    return True

  mocker.patch.object(iotc,'send_property',return_value=True)
  await iotc.connect()
  iotc.on(IOTCEvents.IOTC_PROPERTIES,onProps)

  try:
    await iotc._prop_thread
  except asyncio.CancelledError:
    pass



@pytest.mark.asyncio
async def test_on_commands_before(mocker):

  iotc = init(mocker)

  async def onCmds(command,ack):
    ret=ack()
    assert ret=='mocked'
    await stop_threads(iotc)
    return True


  def mockedAck():
    return 'mocked'

  mocker.patch.object(iotc,'_cmd_ack',mockedAck)

  iotc.on(IOTCEvents.IOTC_COMMAND,onCmds)
  await iotc.connect()
  try:
    await iotc._cmd_thread
  except asyncio.CancelledError:
    pass

@pytest.mark.asyncio
async def test_onCommands_after(mocker):

  iotc = init(mocker)

  async def onCmds(command,ack):
    ret=ack()
    assert ret=='mocked'
    await stop_threads(iotc)
    return True


  def mockedAck():
    return 'mocked'

  mocker.patch.object(iotc,'_cmd_ack',mockedAck)

  await iotc.connect()
  iotc.on(IOTCEvents.IOTC_COMMAND,onCmds)

  try:
    await iotc._cmd_thread
  except asyncio.CancelledError:
    pass

