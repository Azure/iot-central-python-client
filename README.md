# Microsoft Azure IoTCentral SDK for Python

[![Join the chat at https://gitter.im/iotdisc/community](https://badges.gitter.im/iotdisc.svg)](https://gitter.im/iotdisc/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Licensed under the MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/lucadruda/iotc-python-device-client/blob/master/LICENSE)
[![PyPI version](https://badge.fury.io/py/iotc.svg)](https://badge.fury.io/py/iotc)

### An Azure IoT Central device client library written in Python.

This repository contains code for the Azure IoT Central SDK for Python. This enables python developers to easily create device solutions that semealessly connect to Azure IoT Central applications.
It hides some of the complexities of the official Azure IoT SDK and uses IoT Central naming conventions.

### Disclaimer

> **This library is experimental and has the purpose of providing an easy to use solution for prototyping and small projects. Its use in production is discouraged.
The library is going to be archived soon so we suggest new developments to start using official Azure IoT SDK.**

> **Please refer to [Azure IoT Python SDK](https://github.com/Azure/azure-iot-sdk-python) when building production products.**

_If you're looking for the v0.x.x client library, it is now preserved [here](https://github.com/obastemur/iot_client/tree/master/python).
Latest version on pypi is 0.3.9_

## Prerequisites

- Python 2.7+ or Python 3.7+ (recommended)

## Installing `iotc`

```
pip install iotc
```

These clients are available with an asynchronous API, as well as a blocking synchronous API for compatibility scenarios. **We recommend you use Python 3.7+ and the asynchronous API.**

| Python Version | Asynchronous API | Synchronous API |
| -------------- | ---------------- | --------------- |
| Python 3.5.3+  | **YES**          | **YES**         |
| Python 2.7     | NO               | **YES**         |

## Samples

Check out the [sample repository](samples) for example code showing how the SDK can be used in the various scenarios:

- [async_device_key](samples/async_device_key.py) - Sending telemetry and receiving properties and commands with device connected through **symmetric key** (Python 3.7+)
- [async_x509](samples/async_x509.py) - Sending telemetry and receiving properties and commands with device connected through **x509 certificates** (Python 3.7+)
- [async_file_logger](samples/async_file_logger.py) - Print logs on file with rotation (Python 3.7+)
- [async_eventhub_logger](samples/async_eventhub_logger.py) - Redirect logs to Azure Event Hub (Python 3.7+)

**The following samples are legacy samples**, they work with the sycnhronous API intended for use with Python 2.7, or in compatibility scenarios with later versions. We recommend you use the asynchronous API and Python3 samples above instead.

- [sync_device_key](samples/sync_device_key.py) - Sending telemetry and receiving properties and commands with device connected through **symmetric key** (Python 2.7+)
- [sync_x509](samples/sync_x509.py) - Sending telemetry and receiving properties and commands with device connected through **x509 certificates** (Python 2.7+)

Samples by default parse a configuration file including required credentials. Just create a file called **samples.ini** inside the _samples_ folder with a content like this:

```ini
[DEVICE_A]
ScopeId = scopeid
DeviceId = deviceid
; either one or the other or nothing if running with certificates
DeviceKey = device_key
GroupKey = group_key
; none if running with keys
CertFilePath = path_to_cert_file
KeyFilePath = path_to_key_file
CertPassphrase = optional password
```

The configuration file can include one or more sections representing device connection details. Section names must match references in the sample file.

### Run samples with local changes

It is possible to run samples against the local copy of the device client. This is particularly useful when testing patches not yet published upstream.
Just add an entry to **samples.ini** in the _DEFAULT_ section:

```ini
[DEFAULT]
Local = yes
```

## Importing the module

Sync client (Python 2.7+ and 3.7+) can be imported in this way:

```py
from iotc import IoTCClient
```

Async client (with asyncio for Python 3.7+ only) can be imported like this:

```py
from iotc.aio import IoTCClient
```

## Connecting

#### X509

```py
scope_id = 'scope_id';
device_id = 'device_id';
key = {'certFile':'<CERT_CHAIN_FILE_PATH>','keyFile':'<CERT_KEY_FILE_PATH>','certPhrase':'<CERT_PASSWORD>'}

iotc = IoTCClient(device_id, scope_id,
                  IOTCConnectType.IOTC_CONNECT_X509_CERT, key)
```

IOTCConnectType enum can be imported from the same module of IoTCClient

_'certPhrase'_ is optional and represents the password for the certificate if any

**_A handy tool to generate self-signed certificates in order to test x509 authentication can be found in the IoTCentral Node.JS SDK [here.](https://github.com/lucadruda/iotc-nodejs-device-client#generate-x509-certificates)_**

#### SAS

```py
scopeId = 'scopeID'
device_id = 'device_id'
sasKey = 'masterKey' # or use device key directly

iotc = IoTCClient(device_id, scopeId,
                  IOTCConnectType.IOTC_CONNECT_SYMM_KEY, sas_key)
```

IOTCConnectType enum can be imported from the same module of IoTCClient

### Connect

Sync

```
iotc.connect()
```

Async

```py
await iotc.connect()
```

After successfull connection, IOTC context is available for further commands.

### Reconnection

The device client automatically handle reconnection in case of network failures or disconnections. However if process runs for long time (e.g. unmonitored devices) a reconnection might fail because of credentials expiration.

To control reconnection and reset credentials the function _is_connected()_ is available and can be used to test connection status inside a loop or before running operations.

e.g.

```py
retry = 0 # stop reconnection attempts
while true:
    if iotc.is_connected():
        # do something
    else
        if retry == 10:
            sys.exit("error")
        retry += 1
        iotc.connect()
```

## Cache Credentials

The IoT Central device client accepts a storage manager to cache connection credentials. This allows to skip unnecessary device re-provisioning and requests to provisioning service.
When valid credentials are present, device connects directly to IoT Central, otherwise it asks provisioning service for new credentials and eventually cache them.

Provided class must extend [_Storage_](src/iotc/models.py) abstract class.

```py
class FileStorage(Storage):
    def __init__(self):
        # initialize file read
        ...
    def retrieve(self):
        # read from file
        ...
        return CredentialsCache(
            hub_name,
            device_id,
            key,
        )
    def persist(self, credentials):
        # write to file
        ...
```

## Operations

### Send telemetry

e.g. Send telemetry every 3 seconds

```py
while iotc.is_connected():
        await iotc.send_telemetry({
            'accelerometerX': str(randint(20, 45)),
            'accelerometerY': str(randint(20, 45)),
            "accelerometerZ": str(randint(20, 45))
        })
        time.sleep(3)
```

An optional _properties_ object can be included in the send methods, to specify additional properties for the message (e.g. timestamp,etc... ).
Properties can be custom or part of the reserved ones (see list [here](https://github.com/Azure/azure-iot-sdk-csharp/blob/master/iothub/device/src/MessageSystemPropertyNames.cs#L36)).

> Payload content type and encoding are set by default to 'application/json' and 'utf-8'. Alternative values can be set using these functions:<br/>
> _iotc.set_content_type(content_type)_ # .e.g 'text/plain'
> _iotc.set_content_encoding(content_encoding)_ # .e.g 'ascii'

### Send property update

```py
iotc.send_property({'fieldName':'fieldValue'})
```

### Listen to properties update

```py
iotc.on(IOTCEvents.IOTC_PROPERTIES, callback)
```

To provide setting sync aknowledgement, the callback must reply **True** if the new value has been applied or **False** otherwise

```py
async def on_props(prop_name, prop_value):
    print(prop_value)
    return True

iotc.on(IOTCEvents.IOTC_PROPERTIES, on_props)
```

### Listen to commands

```py
iotc.on(IOTCEvents.IOTC_COMMAND, callback)
```

To provide feedbacks for the command like execution result or progress, the client can call the **ack** function available in the callback.

The function accepts 3 arguments: command name, a custom response message and the request id for which the ack applies.

```py
async def on_commands(command, ack):
    print(command.name)
    await ack(command.name, 'Command received', command.request_id)
```

## Logging

The default log prints to console operations status and errors.
This is the _IOTC_LOGGING_API_ONLY_ logging level.
The function **set_log_level()** can be used to change options or disable logs. It accepts a _IOTCLogLevel_ value among the following:

- IOTC_LOGGING_DISABLED (log disabled)
- IOTC_LOGGING_API_ONLY (information and errors, default)
- IOTC_LOGGING_ALL (all messages, debug and underlying errors)

The device client also accepts an optional Logger instance to redirect logs to other targets than console.
The custom class must implement three methods:

- info(message)
- debug(message)
- set_log_level(message);

## One-touch device provisioning and approval

A device can send custom data during provision process: if a device is aware of its IoT Central template Id, then it can be automatically provisioned.

### How to set IoTC template ID in your device

Template Id can be found in the device explorer page of IoTCentral
![Img](https://github.com/iot-for-all/iotc-python-client/raw/master/assets/modelId.jpg)

Then call this method before connect():

```py
iotc.set_model_id('<modelId>')
```

### Manual approval (default)

By default device auto-approval in IoT Central is disabled, which means that administrator needs to approve the device registration to complete the provisioning process.
This can be done from explorer page after selecting the device
![Img](https://github.com/iot-for-all/iotc-python-client/raw/master/assets/manual_approval.jpg)

### Automatic approval

To change default behavior, administrator can enable device auto-approval from Device Connection page under the Administration section.
With automatic approval a device can be provisioned without any manual action and can start sending/receiving data after status changes to "Provisioned"

![Img](https://github.com/iot-for-all/iotc-python-client/raw/master/assets/auto_approval.jpg)

## License

This samples is licensed with the MIT license. For more information, see [LICENSE](./LICENSE)
