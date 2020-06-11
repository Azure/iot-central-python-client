import os
import asyncio
import configparser
import sys

from random import randint

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__),'samples.ini'))

if config['DEFAULT'].getboolean('Local'):
    sys.path.insert(0, 'src')

from iotc import IOTCConnectType, IOTCLogLevel, IOTCEvents
from iotc.aio import IoTCClient

device_id = config['DEVICE_A']['DeviceId']
scope_id = config['DEVICE_A']['ScopeId']
key = config['DEVICE_A']['DeviceKey']

# optional model Id for auto-provisioning
try:
    model_id = config['DEVICE_A']['ModelId']
except:
    model_id = None


async def on_props(propName, propValue):
    print(propValue)
    return True


async def on_commands(command, ack):
    print(command.name)
    await ack(command.name, 'Command received', command.request_id)

async def on_enqueued_commands(command_name,command_data):
    print(command_name)
    print(command_data)

# change connect type to reflect the used key (device or group)
client = IoTCClient(device_id, scope_id,
                  IOTCConnectType.IOTC_CONNECT_DEVICE_KEY, key)
if model_id != None:
    client.set_model_id(model_id)

client.set_log_level(IOTCLogLevel.IOTC_LOGGING_ALL)
client.on(IOTCEvents.IOTC_PROPERTIES, on_props)
client.on(IOTCEvents.IOTC_COMMAND, on_commands)
client.on(IOTCEvents.IOTC_ENQUEUED_COMMAND, on_enqueued_commands)

# iotc.setQosLevel(IOTQosLevel.IOTC_QOS_AT_MOST_ONCE)

async def command_loop(device_client):
    while True:
        # Wait for unknown method calls
        method_request = (await device_client.receive_method_request())
        print('Received command {}'.format(method_request.name))
        await device_client.send_method_response(MethodResponse.create_from_method_request(
            method_request, 200, {
                'result': True, 'data': 'Command received'}
        ))

async def main():
    await client.connect()
    while client.is_connected():
        await client.send_telemetry({
            't777b192a': str(randint(20, 45)),
            'h6941c57b': str(randint(20, 45)),
            "b2fba1eb1": str(randint(20, 45))
        })
        await asyncio.sleep(3)
    

asyncio.run(main())
