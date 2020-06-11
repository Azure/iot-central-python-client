import sys
import os
import asyncio
import configparser
from random import randint
from azure.eventhub.aio import EventHubProducerClient
from azure.eventhub import EventData

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'samples.ini'))

if config['DEFAULT'].getboolean('Local'):
    sys.path.insert(0, 'src')

from iotc import IOTCConnectType, IOTCLogLevel, IOTCEvents
from iotc.aio import IoTCClient

# Change config section name to reflect sample.ini
device_id = config['DEVICE_A']['DeviceId']
scope_id = config['DEVICE_A']['ScopeId']
key = config['DEVICE_A']['DeviceKey']

event_hub_conn_str = config['EventHub']['ConnectionString']
event_hub_name = config['EventHub']['EventHubName']

# optional model Id for auto-provisioning
try:
    model_id = config['DEVICE_A']['ModelId']
except:
    model_id = None


class EventHubLogger:
    def __init__(self, conn_str, eventhub_name):
        self._producer = EventHubProducerClient.from_connection_string(conn_str, eventhub_name=eventhub_name)

    async def _create_batch(self):
        self._event_data_batch = await self._producer.create_batch()

    async def _log(self, message):
        event_data_batch = await self._producer.create_batch()
        event_data_batch.add(EventData(message))
        await self._producer.send_batch(event_data_batch)

    async def info(self, message):
        if self._log_level != IOTCLogLevel.IOTC_LOGGING_DISABLED:
            await self._log(message)

    async def debug(self, message):
        if self._log_level == IOTCLogLevel.IOTC_LOGGING_ALL:
            await self._log(message)

    def set_log_level(self, log_level):
        self._log_level = log_level


async def on_props(propName, propValue):
    print(propValue)
    return True


async def on_commands(command, ack):
    print(command.name)
    await ack(command.name, 'Command received', command.request_id)


# change connect type to reflect the used key (device or group)
client = IoTCClient(device_id, scope_id,
                  IOTCConnectType.IOTC_CONNECT_DEVICE_KEY, key, EventHubLogger(event_hub_conn_str, event_hub_name))
if model_id != None:
    client.set_model_id(model_id)

client.set_log_level(IOTCLogLevel.IOTC_LOGGING_ALL)
client.on(IOTCEvents.IOTC_PROPERTIES, on_props)
client.on(IOTCEvents.IOTC_COMMAND, on_commands)

# iotc.setQosLevel(IOTQosLevel.IOTC_QOS_AT_MOST_ONCE)


async def main():
    await client.connect()
    while client.is_connected():
        await client.send_telemetry({
            'accelerometerX': str(randint(20, 45)),
            'accelerometerY': str(randint(20, 45)),
            "accelerometerZ": str(randint(20, 45))
        })
        await asyncio.sleep(3)


asyncio.run(main())
