import sys
sys.path.insert(1, 'src')
import iotc
from iotc import IOTConnectType, IOTLogLevel, IOTQosLevel
from random import randint



deviceId = "py4"
scopeId = "0ne0009AC0E"
key = "djD3Cx3HzdyoX/gLSmw33pNwde/LovdJiXbbzR4ybrDwOBbuKyd17efy/DwDtc91f/kaWQbMqdPqS2buJf5zOA=="

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
    if command_name == "echo":
        resp = command_value
        info.setResponse(200, resp)
    elif command_name == "reboot":
        info.setResponse(200, resp)
        def cb():
            # global gNeedAsync
            iotc.sendCommandUpdate(
                interface_name, command_name, request_id, 200, "Progress")
        info.setCallback(cb)





def onpropertiesupdated(info):
    print("property name:", info.getTag())
    print("property value: ", info.getPayload())


iotc.on("ConnectionStatus", onconnect)
iotc.on("MessageSent", onmessagesent)
iotc.on("Command", oncommand)
iotc.on("Properties", onpropertiesupdated)

iotc.setModelData(
    {"__iot:interfaces": {"CapabilityModelId": "urn:mxchip:mxchip_iot_devkit:2"}})

iotc.setInterfaces({"settings": "urn:mxchip:settings:1", "sensors": "urn:mxchip:built_in_sensors:1",
                    "leds": "urn:mxchip:built_in_leds:1", "screen": "urn:mxchip:screen:2"})
iotc.connect()

registered = False
while iotc.isConnected():
    iotc.doNext()  # do the async work needed to be done for MQTT
    if gCanSend == True:
        if gCounter % 20 == 0:
            gCounter = 0
            iotc.sendTelemetry({"temperature": str(randint(20, 45))}, {
                "$.ifid": 'urn:mxchip:built_in_sensors:1',
                "$.ifname": 'sensors',
                "$.schema": 'temperature'})
            iotc.sendTelemetry({"pressure": str(randint(20, 45))}, {
                "$.ifid": 'urn:mxchip:built_in_sensors:1',
                "$.ifname": 'sensors',
                "$.schema": 'pressure'})

        gCounter += 1
