import sys
sys.path.insert(0, 'src')
import pytest
import mock
from unittest.mock import ANY

from azure.iot.device.provisioning.models import RegistrationResult
from azure.iot.device.iothub.models import MethodRequest

from azure.iotcentral.device.client import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents

groupKey='68p6zEjwVNB6L/Dz8Wkz4VhaTrYqkndPrB0uJbWr2Hc/AmB+Qxz/eJJ9MIhLZFJ6hC0RmHMgfaYBkNTq84OCNQ=='
deviceKey='Jdj7TBhH5RXCD+24bT5PTGf0NwdDbDvsI+rniK2AUHk='
deviceId='nuovodev'
scopeId='0ne00052362'
assignedHub='iotc-632b1fc0-6e52-45d5-a37f-0daf6838f515.azure-devices.net'
expectedHub='HostName=iotc-632b1fc0-6e52-45d5-a37f-0daf6838f515.azure-devices.net;DeviceId=nuovodev;SharedAccessKey=Jdj7TBhH5RXCD+24bT5PTGf0NwdDbDvsI+rniK2AUHk='

class NewRegState():
  def __init__(self):
    self.assigned_hub=assignedHub
  
  def assigned_hub(self):
    return self.assigned_hub

class NewProvClient():
  def register(self):
      reg=RegistrationResult('3o375i827i852','assigned',NewRegState())
      return reg
  

def init():
  return IoTCClient(deviceId, scopeId,
                  IOTCConnectType.IOTC_CONNECT_SYMM_KEY, groupKey)



def test_computeKey():
  iotc=init()
  assert iotc._computeDerivedSymmetricKey(groupKey,deviceId) == deviceKey

# @mock.patch('azure.iotcentral.device.client.IoTHubDeviceClient.connect',return_value=True)
# @mock.patch('azure.iotcentral.device.client.ProvisioningDeviceClient.create_from_symmetric_key',return_value=NewProvClient())
# def test_notConnectedDefault(ioTHubDeviceClient,provisioningDeviceClient):
#   provisioningDeviceClient.create_from_symmetric_key.return_value=provisioningDeviceClient
#   iotc = init()
#   iotc.connect()
#   assert iotc.isConnected() == False

@mock.patch('azure.iotcentral.device.client.IoTHubDeviceClient.connect',return_value=True)
@mock.patch('azure.iotcentral.device.client.ProvisioningDeviceClient.create_from_symmetric_key',return_value=NewProvClient())
def test_deviceKeyGeneration(ioTHubDeviceClient,provisioningDeviceClient):
  iotc = init()
  iotc.connect()
  assert iotc._keyORCert == deviceKey

@mock.patch('azure.iotcentral.device.client.IoTHubDeviceClient.connect',return_value=True)
@mock.patch('azure.iotcentral.device.client.ProvisioningDeviceClient.create_from_symmetric_key',return_value=NewProvClient())
def test_hubConnectionString(ioTHubDeviceClient,provisioningDeviceClient):
  iotc = init()
  iotc.connect()
  assert iotc._hubCString == expectedHub


def test_onproperties(mocker):

  propPayload={'prop1':{'value':40},'$version':5}
  
  mocker.patch('azure.iotcentral.device.client.IoTHubDeviceClient.connect',return_value=True)
  mocker.patch('azure.iotcentral.device.client.IoTHubDeviceClient.receive_twin_desired_properties_patch',return_value=propPayload)
  mocker.patch('azure.iotcentral.device.client.ProvisioningDeviceClient.create_from_symmetric_key',return_value=NewProvClient())
  onProps=mock.Mock()

  
  iotc = init()
  iotc.on(IOTCEvents.IOTC_PROPERTIES,onProps)
  iotc.connect()
  onProps.assert_called_with('prop1',40)


def test_onCommands(mocker):

  cmdRequestId='abcdef'
  cmdName='command1'
  cmdPayload='payload'
  methodRequest=MethodRequest(cmdRequestId,cmdName,cmdPayload)

  mocker.patch('azure.iotcentral.device.client.IoTHubDeviceClient.connect',return_value=True)
  mocker.patch('azure.iotcentral.device.client.IoTHubDeviceClient.receive_method_request',return_value=methodRequest)
  mocker.patch('azure.iotcentral.device.client.ProvisioningDeviceClient.create_from_symmetric_key',return_value=NewProvClient())

  onCmds=mock.Mock()

  iotc = init()
  iotc.on(IOTCEvents.IOTC_COMMAND,onCmds)
  iotc.connect()
  onCmds.assert_called_with(methodRequest)

