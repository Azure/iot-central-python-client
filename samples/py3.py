import sys
sys.path.insert(0, 'src')

import asyncio
from random import randint
from azure.iotcentral.device.client.aio import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents



deviceId = "<DEVICE_ID>"
scopeId = "<SCOPE_ID>"
key = '<DEVICE_OR_GROUP_KEY>'

# optional model Id for auto-provisioning
modelId= '<TEMPLATE_ID>'


async def onProps(propName, propValue):
    print(propValue)
    return True


async def onCommands(command, ack):
    print(command.name)
    await ack(command.name, 'Command received', command.request_id)


# change connect type to reflect the used key (device or group)
iotc = IoTCClient(deviceId, scopeId,
                  IOTCConnectType.IOTC_CONNECT_SYMM_KEY, key)
iotc.setModelId(modelId)
iotc.setLogLevel(IOTCLogLevel.IOTC_LOGGING_ALL)
iotc.on(IOTCEvents.IOTC_PROPERTIES, onProps)
iotc.on(IOTCEvents.IOTC_COMMAND, onCommands)

# iotc.setQosLevel(IOTQosLevel.IOTC_QOS_AT_MOST_ONCE)


async def main():
    await iotc.connect()
    while iotc.isConnected():
        await iotc.sendTelemetry({
            'accelerometerX': str(randint(20, 45)),
            'accelerometerY': str(randint(20, 45)),
            "accelerometerZ": str(randint(20, 45))
        })
        await asyncio.sleep(3)


asyncio.run(main())
