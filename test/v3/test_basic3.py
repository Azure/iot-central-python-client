import sys
sys.path.insert(0, 'src')
import pytest
import mock
import time
import asyncio

from contextlib import suppress

from azure.iot.device.provisioning.models import RegistrationResult
from azure.iot.device.iothub.models import MethodRequest

from azure.iotcentral.device.client.aio import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents

groupKey='68p6zEjwVNB6L/Dz8Wkz4VhaTrYqkndPrB0uJbWr2Hc/AmB+Qxz/eJJ9MIhLZFJ6hC0RmHMgfaYBkNTq84OCNQ=='
deviceKey='Jdj7TBhH5RXCD+24bT5PTGf0NwdDbDvsI+rniK2AUHk='
deviceId='nuovodev'
scopeId='0ne00052362'
assignedHub='iotc-632b1fc0-6e52-45d5-a37f-0daf6838f515.azure-devices.net'
expectedHub='HostName=iotc-632b1fc0-6e52-45d5-a37f-0daf6838f515.azure-devices.net;DeviceId=nuovodev;SharedAccessKey=Jdj7TBhH5RXCD+24bT5PTGf0NwdDbDvsI+rniK2AUHk='

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


async def stopThreads(iotc):
  iotc._propThread.cancel()
  iotc._cmdThread.cancel()
  
  
@pytest.mark.asyncio
def init(mocker):
  iotc=IoTCClient(deviceId, scopeId,
                  IOTCConnectType.IOTC_CONNECT_SYMM_KEY, groupKey)
  mocker.patch('azure.iotcentral.device.client.aio.ProvisioningDeviceClient.create_from_symmetric_key',return_value=NewProvClient())
  mocker.patch('azure.iotcentral.device.client.aio.IoTHubDeviceClient.create_from_connection_string',return_value=NewDeviceClient())
  return iotc



@pytest.mark.asyncio
async def test_computeKey(mocker):
  iotc=init(mocker)
  assert iotc._computeDerivedSymmetricKey(groupKey,deviceId) == deviceKey

@pytest.mark.asyncio
async def test_deviceKeyGeneration(mocker):
  iotc = init(mocker)
  await iotc.connect()
  assert iotc._keyORCert == deviceKey
  await stopThreads(iotc)


@pytest.mark.asyncio
async def test_hubConnectionString(mocker):
  iotc = init(mocker)
  await iotc.connect()
  assert iotc._hubCString == expectedHub
  await stopThreads(iotc)


@pytest.mark.asyncio
async def test_onproperties_before(mocker):
  iotc = init(mocker)

  async def onProps(propname,propvalue):
    assert propname == 'prop1'
    assert propvalue == 40
    await stopThreads(iotc)

  mocker.patch.object(iotc,'sendProperty',return_value=True)
  iotc.on(IOTCEvents.IOTC_PROPERTIES,onProps)
  await iotc.connect()
  try:
    await iotc._propThread
    await iotc._cmdThread
  except asyncio.CancelledError:
    pass
 


@pytest.mark.asyncio
async def test_onproperties_after(mocker):
  iotc = init(mocker)
  
  async def onProps(propname,propvalue):
    assert propname == 'prop1'
    assert propvalue == 40
    await stopThreads(iotc)
    return True

  mocker.patch.object(iotc,'sendProperty',return_value=True)
  await iotc.connect()
  iotc.on(IOTCEvents.IOTC_PROPERTIES,onProps)

  try:
    await iotc._propThread
  except asyncio.CancelledError:
    pass



@pytest.mark.asyncio
async def test_onCommands_before(mocker):

  iotc = init(mocker)

  async def onCmds(command,ack):
    ret=ack()
    assert ret=='mocked'
    await stopThreads(iotc)
    return True


  def mockedAck():
    return 'mocked'

  mocker.patch.object(iotc,'_cmdAck',mockedAck)

  iotc.on(IOTCEvents.IOTC_COMMAND,onCmds)
  await iotc.connect()
  try:
    await iotc._cmdThread
  except asyncio.CancelledError:
    pass

@pytest.mark.asyncio
async def test_onCommands_after(mocker):

  iotc = init(mocker)

  async def onCmds(command,ack):
    ret=ack()
    assert ret=='mocked'
    await stopThreads(iotc)
    return True


  def mockedAck():
    return 'mocked'

  mocker.patch.object(iotc,'_cmdAck',mockedAck)

  await iotc.connect()
  iotc.on(IOTCEvents.IOTC_COMMAND,onCmds)

  try:
    await iotc._cmdThread
  except asyncio.CancelledError:
    pass

