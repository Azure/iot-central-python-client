import sys
sys.path.insert(0, '../src')

import time
import asyncio
from random import randint
from azure.iotcentral.device.client.aio import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents



deviceId = "nuovodev"
scopeId = "0ne00052362"
key = '68p6zEjwVNB6L/Dz8Wkz4VhaTrYqkndPrB0uJbWr2Hc/AmB+Qxz/eJJ9MIhLZFJ6hC0RmHMgfaYBkNTq84OCNQ=='


async def onProps(propName, propValue):
    print(propValue)
    return True


async def onCommands(command, ack):
    print(command.name)
    await ack(command.name, 'Command received', command.request_id)


# see iotc.Device documentation above for x509 argument sample
iotc = IoTCClient(deviceId, scopeId,
                  IOTCConnectType.IOTC_CONNECT_SYMM_KEY, key)
iotc.setModelId('c318d580-39fc-4aca-b995-843719821049/1.5.0')
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
        time.sleep(3)


asyncio.run(main())
