## iotc - Azure IoT Central - Python (light) device SDK Documentation

### Prerequisites

Python 2.7+ or Python 3.4+ or Micropython 1.9+

*Runtime dependencies vary per platform*

### Install

Python 2/3
```
pip install iotc
```

### Common Concepts

- API calls should return `0` on success and `error code` otherwise.
- External API naming convention follows `lowerCamelCase` for `Device` class members
- Asyncronous commands must be acknowledge as any other sync commands but execution updates should be sent through the `sendCommand` function

### Usage

```
import iotc
device = iotc.Device(scopeId, keyORCert, deviceId, credType)
```

- *scopeId*    : Azure IoT DPS Scope Id
- *keyORcert*  : Group or device symmetric key or x509 Certificate
- *deviceId*   : Device Id
- *credType*   : `IOTConnectType.IOTC_CONNECT_SYMM_KEY`,`IOTConnectType.IOTC_CONNECT_DEVICE_KEY` or `IOTConnectType.IOTC_CONNECT_X509_CERT`

`keyORcert` for `X509` certificate:
```
credType = IOTConnectType.IOTC_CONNECT_X509_CERT
keyORcert = {
  "keyfile": "/src/python/test/device.key.pem",
  "certfile": "/src/python/test/device.cert.pem"
}
```

`keyORcert` for `SAS` token:
```
credType = IOTConnectType.IOTC_CONNECT_SYMM_KEY
keyORcert = "xxxxxxxxxxxxxxx........"
```

#### setLogLevel
set logging level
```
device.setLogLevel(logLevel)
```

*logLevel*   : (default value is `IOTC_LOGGING_DISABLED`)
```
class IOTLogLevel:
  IOTC_LOGGING_DISABLED =  1
  IOTC_LOGGING_API_ONLY =  2
  IOTC_LOGGING_ALL      = 16
```

*i.e.* => `device.setLogLevel(IOTLogLevel.IOTC_LOGGING_API_ONLY)`

#### setExitOnError
enable/disable application termination on mqtt later exceptions. (default false)
```
device.setExitOnError(isEnabled)
```

*i.e.* => `device.setExitOnError(True)`

#### setModelData
set the device model data (if any)
```
device.setModelData(modelJSON)
```

*modelJSON*  : Device model definition.

*i.e.* => `device.setModelData({"__iot:interfaces": {"CapabilityModelId": "<PUT_MODEL_ID_HERE>"}})`

#### setInterfaces
set the interfaces exposed by the device. If interfaces are not declared, related properties and commands will not be received by the device and telemetry will have no effect
```
device.setInterfaces(interfaceJSON)
```

*interfacesJSON* : Interfaces object

*i.e.* => `device.setInterfaces({"[PUT_INTERFACE_1_NAME_HERE]": "[PUT_INTERFACE_1_ID_HERE]", ... ,"[PUT_INTERFACE_N_NAME_HERE]": "[PUT_INTERFACE_N_ID_HERE]"})`

#### setTokenExpiration
set the token expiration timeout. default is 21600 seconds (6 hours)
```
device.setTokenExpiration(totalSeconds)
```

*totalSeconds*  : timeout in seconds.

*i.e.* => `device.setTokenExpiration(600)`

#### setServiceHost
set the service endpoint URL
```
device.setServiceHost(url)
```

*url*    : URL for service endpoint. (default value is `global.azure-devices-provisioning.net`)

*call this before connect*

#### setQosLevel
Set the MQTT Quality of Service (QoS) level desired for all MQTT publish calls
```
device.setQosLevel(qosLevel)
```

*qosLevel*   : (default value is `IOTC_QOS_AT_MOST_ONCE`)
```
class IOTQosLevel:
  IOTC_QOS_AT_MOST_ONCE  = 0
  IOTC_QOS_AT_LEAST_ONCE = 1
```

Note: IOTC_QOS_AT_LEAST_ONCE will have slower performance than IOTC_QOS_AT_MOST_ONCE as the MQTT client must store the value for possible replay and also wait for an acknowledgement from the IoT Hub that the MQTT message has been received.  Think of IOTC_QOS_AT_MOST_ONCE as "fire and forget" vs. IOTC_QOS_AT_LEAST_ONCE as "guaranteed delivery".  As the developer you should consider the importance of 100% data delivery vs. increased connection time and data traffic over the data connection.

*call this before connect*

#### connect
connect device client  `# blocking`. Raises `ConnectionStatus` event.

```
device.connect()
```

or

```
device.connect(hostName)
```

*i.e.* => `device.connect()`

#### sendTelemetry
send telemetry

```
device.sendTelemetry(payload, [[optional system properties]])
```

*payload*  : A text payload.

*i.e.* => `device.sendTelemetry('{ "temperature": 15 }')`

You may also set system properties for the telemetry message. See also [iothub message format](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-messages-construct)

*i.e.* => `device.sendTelemetry('{ "temperature":22 }', {"iothub-creation-time-utc": time.time()})`

#### sendState
send device state

```
device.sendState(payload)
```

*payload*  : A text payload.

*i.e.* => `device.sendState('{ "status": "WARNING"}')`

#### sendProperty
send reported property

```
device.sendProperty(payload)
```

*payload*  : A text payload.

*i.e.* => `device.sendProperty('{"countdown":{"value": %d}}')`

#### sendCommandUpdate
send execution updates for asyncronous messages

```
device.sendCommandUpdate(interface_name, command_name, request_id, status_code, update_message)
```

*interface_name*  : Command interface name.
*command_name*  : Command name.
*request_id*  : Request Id for the command. This must be the same value received for the command in on("Command"). Can be obtain by calling _getPayload()["requestId"]_ of the callback object (see example)
*status_code*  : Update status code.
*update_message*  : A text message.


*i.e.* => `device.sendCommandUpdate("commands", "reboot", "a4795148-155f-4d75-92bf-3536bc0cbcee", 200, "Progress")`
`

#### doNext
let framework do the partial MQTT work.

```
device.doNext()
```

#### isConnected
returns whether the connection was established or not.

```
device.isConnected()
```

*i.e.* => `device.isConnected()`

#### disconnect
disconnect device client

```
device.disconnect()
```

*i.e.* => `device.disconnect()`

#### getDeviceProperties
pulls latest twin data (device properties). Raises `PropertiesUpdated` event.

```
device.getDeviceProperties()
```

*i.e.* => `device.getDeviceProperties()`

#### getHostName
returns the iothub hostname cached during the initial connection.

```
device.getHostName()
```

*i.e.* => `device.getDeviceHostName()`

#### on
set event callback to listen events

- `ConnectionStatus` : connection status has changed
- `MessageSent`      : message was sent
- `Command`          : a command received from Azure IoT Central
- `PropertiesUpdated`  : device properties were updated

i.e.
```
def onconnect(info):
  if info.getStatusCode() == 0:
    print("connected!")

device.on("ConnectionStatus", onconnect)
```

```
def onmessagesent(info):
  print("message sent -> " + info.getPayload())

device.on("MessageSent", onmessagesent)
```

```
def oncommand(info):
  print("command name:", info.getTag())
  print("command args: ", info.getPayload())

device.on("Command", oncommand)
```

```
def onpropertiesupdated(info):
  print("property name:", info.getTag())
  print("property value: ", info.getPayload())

device.on("Updated", onpropertiesupdated)
```

#### callback info class

`iotc` callbacks have a single argument derived from `IOTCallbackInfo`.
Using this interface, you can get the callback details and respond back when it's necessary.

public members of `IOTCallbackInfo` are;

`getResponseCode()` : get response code or `None`

`getResponseMessage()` : get response message or `None`

`setResponse(responseCode, responseMessage)` : set callback response

*i.e.* => `info.setResponse(200, 'completed')`

`getClient()` : get active `device` client

`getEventName()` : get the name of the event

`getPayload()` : get the payload or `None`

`getTag()` : get the tag or `None`

`getStatusCode()` : get callback status code

#### sample app

```
import iotc
from iotc import IOTConnectType, IOTLogLevel, IOTQosLevel
from random import randint

deviceId = "DEVICE_ID"
scopeId = "SCOPE_ID"
key = "SYMM_KEY"

# see iotc.Device documentation above for x509 argument sample
iotc = iotc.Device(scopeId, key, deviceId,
                   IOTConnectType.IOTC_CONNECT_SYMM_KEY)
iotc.setLogLevel(IOTLogLevel.IOTC_LOGGING_ALL)
iotc.setQosLevel(IOTQosLevel.IOTC_QOS_AT_MOST_ONCE)

gCanSend = False
gCounter = 0


def onconnect(info):
    global gCanSend
    print("- [onconnect] => status:" + str(info.getStatusCode()))
    if info.getStatusCode() == 0:
        if iotc.isConnected():
            gCanSend = True


def onmessagesent(info):
    print("\t- [onmessagesent] => " + str(info.getPayload()))


def oncommand(info):
    interface_name = info.getInterface()
    command_name = info.getTag()
    request_id = None
    try:
        command_value = info.getPayload()["value"]
        request_id = info.getPayload()["requestId"]
    except:
        command_value = info.getPayload()
    resp = "Received"
    info.setResponse(200,resp)


def onpropertiesupdated(info):
    print("property name:", info.getTag())
    print("property value: ", info.getPayload())


iotc.on("ConnectionStatus", onconnect)
iotc.on("MessageSent", onmessagesent)
iotc.on("Command", oncommand)
iotc.on("Properties", onpropertiesupdated)

iotc.setModelData(
    {"__iot:interfaces": {"CapabilityModelId": "MODEL_ID"}})

# Put interfaces for the specified model
iotc.setInterfaces({"IFNAME": "IFID"})
iotc.connect()

registered = False
while iotc.isConnected():
    iotc.doNext()  # do the async work needed to be done for MQTT
    if gCanSend == True:
        if gCounter % 20 == 0:
            gCounter = 0
            iotc.sendTelemetry({"temperature": str(randint(20, 45))}, {
                "$.ifid": 'IFID',
                "$.ifname": 'IFNAME',
                "$.schema": 'temperature'})
            iotc.sendTelemetry({"pressure": str(randint(20, 45))}, {
                "$.ifid": 'IFID',
                "$.ifname": 'IFNAME',
                "$.schema": 'pressure'})

        gCounter += 1
```