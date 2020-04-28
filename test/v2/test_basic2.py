import sys
sys.path.insert(0, 'src')
import pytest
import mock
import time

from azure.iot.device.provisioning.models import RegistrationResult
from azure.iot.device.iothub.models import MethodRequest

from azure.iotcentral.device.client import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents

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
  def register(self):
      reg=RegistrationResult('3o375i827i852','assigned',NewRegState())
      return reg

class NewDeviceClient():
  def connect(self):
    return True

  def receive_twin_desired_properties_patch(self):
    return propPayload
  
  def receive_method_request(self):
    return methodRequest

  def send_method_response(self,payload):
    return True
  
  def patch_twin_reported_properties(self,payload):
    return True

  

def init(mocker):
  iotc=IoTCClient(deviceId, scopeId,
                  IOTCConnectType.IOTC_CONNECT_SYMM_KEY, groupKey)
  mocker.patch('azure.iotcentral.device.client.ProvisioningDeviceClient.create_from_symmetric_key',return_value=NewProvClient())
  mocker.patch('azure.iotcentral.device.client.IoTHubDeviceClient.create_from_connection_string',return_value=NewDeviceClient())
  return iotc




def test_computeKey(mocker):
  iotc=init(mocker)
  assert iotc._computeDerivedSymmetricKey(groupKey,deviceId) == deviceKey


def test_deviceKeyGeneration(mocker):
  iotc = init(mocker)
  iotc.connect()
  assert iotc._keyORCert == deviceKey


def test_hubConnectionString(mocker):
  iotc = init(mocker)
  iotc.connect()
  assert iotc._hubCString == expectedHub


def test_onproperties_before(mocker):
  onProps=mock.Mock()
  
  iotc = init(mocker)
  mocker.patch.object(iotc,'sendProperty',mock.Mock())
  iotc.on(IOTCEvents.IOTC_PROPERTIES,onProps)
  iotc.connect()
  onProps.assert_called_with('prop1',40)


def test_onproperties_after(mocker):
  onProps=mock.Mock()
  
  iotc = init(mocker)
  mocker.patch.object(iotc,'sendProperty',mock.Mock())
  iotc.connect()
  iotc.on(IOTCEvents.IOTC_PROPERTIES,onProps)
    # give at least 10 seconds for the new listener to be recognized. assign the listener after connection is discouraged
  time.sleep(11)
  onProps.assert_called_with('prop1',40)

def test_onCommands_before(mocker):

  onCmds=mock.Mock()

  def mockedAck():
    print('Callback called')
    return True

  iotc = init(mocker)
  mocker.patch.object(iotc,'_cmdAck',mockedAck)

  iotc.on(IOTCEvents.IOTC_COMMAND,onCmds)
  iotc.connect()
  onCmds.assert_called_with(methodRequest,mockedAck)

def test_onCommands_after(mocker):

  onCmds=mock.Mock()

  def mockedAck():
    print('Callback called')
    return True

  iotc = init(mocker)
  mocker.patch.object(iotc,'_cmdAck',mockedAck)

  iotc.connect()
  iotc.on(IOTCEvents.IOTC_COMMAND,onCmds)

  # give at least 10 seconds for the new listener to be recognized. assign the listener after connection is discouraged
  time.sleep(11)
  onCmds.assert_called_with(methodRequest,mockedAck)

