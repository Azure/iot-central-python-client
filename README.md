# Microsoft Azure IoTCentral SDK for Python

[![Join the chat at https://gitter.im/iotdisc/community](https://badges.gitter.im/iotdisc.svg)](https://gitter.im/iotdisc/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Licensed under the MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/lucadruda/iotc-python-device-client/blob/master/LICENSE)


## Prerequisites
+ Python 2.7+ or Python 3.7+ (recommended)

## Installing `azure-iotcentral-device-client`

```
pip install azure-iotcentral-device-client
```

## Importing the module
Sync client (Python 2.7+ and 3.7+) can be imported in this way:

```
from azure.iotcentral.device.client import IoTCClient
```
Async client (with asyncio for Python 3.7+ only) can be imported like this:

```
from azure.iotcentral.device.client.aio import IoTCClient
```

## Connecting

#### X509
```
const iotCentral = require('azure-iotcentral-device-client');

const scopeId = '';
const deviceId = '';
const passphrase = ''; //optional
const cert = {
    cert: "public cert"
    key: "private key",
    passphrase: "passphrase"
}

const iotc = new iotCentral.IoTCClient(deviceId, scopeId, 'X509_CERT', cert);
```

#### SAS
```
scopeId = 'scopeID';
deviceId = 'deviceID';
sasKey = 'masterKey'; # or use device key directly

iotc = IoTCClient(deviceId, scopeId,
                  IOTCConnectType.IOTC_CONNECT_SYMM_KEY, sasKey)
```
IOTCConnectType enum can be imported from the same module of IoTCClient

### Connect
Sync
```
iotc.connect()
```
Async
```
await iotc.connect()
```
After successfull connection, IOTC context is available for further commands.


### Send telemetry

e.g. Send telemetry every 3 seconds
```
while iotc.isConnected():
        await iotc.sendTelemetry({
            'accelerometerX': str(randint(20, 45)),
            'accelerometerY': str(randint(20, 45)),
            "accelerometerZ": str(randint(20, 45))
        })
        time.sleep(3)
```
An optional *properties* object can be included in the send methods, to specify additional properties for the message (e.g. timestamp, content-type etc... ).
Properties can be custom or part of the reserved ones (see list [here](https://github.com/Azure/azure-iot-sdk-csharp/blob/master/iothub/device/src/MessageSystemPropertyNames.cs#L36)).

### Send property update
```
iotc.sendProperty({'fieldName':'fieldValue'});
```
### Listen to properties update
```
iotc.on(IOTCEvents.IOTC_PROPERTIES, callback);
```
To provide setting sync aknowledgement, the callback must reply **True** if the new value has been applied or **False** otherwise
```
async def onProps(propName, propValue):
    print(propValue)
    return True

iotc.on(IOTCEvents.IOTC_PROPERTIES, onProps);
```

### Listen to commands
```
iotc.on(IOTCEvents.IOTC_COMMAND, callback)
```
To provide feedbacks for the command like execution result or progress, the client can call the **ack** function available in the callback.

The function accepts 3 arguments: command name, a custom response message and the request id for which the ack applies.
```
async def onCommands(command, ack):
    print(command.name)
    await ack(command.name, 'Command received', command.request_id)
```

## One-touch device provisioning and approval
A device can send custom data during provision process: if a device is aware of its IoT Central template Id, then it can be automatically provisioned.

### How to set IoTC template ID in your device
Template Id can be found in the device explorer page of IoTCentral
![Img](assets/modelId.jpg)

Then call this method before connect():

```
iotc.setModelId('<modelId>');
```

### Manual approval (default)
By default device auto-approval in IoT Central is disabled, which means that administrator needs to approve the device registration to complete the provisioning process.
This can be done from explorer page after selecting the device
![Img](assets/manual_approval.jpg)


### Automatic approval
To change default behavior, administrator can enable device auto-approval from Device Connection page under the Administration section.
With automatic approval a device can be provisioned without any manual action and can start sending/receiving data after status changes to "Provisioned"

![Img](assets/auto_approval.jpg)
