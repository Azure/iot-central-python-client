import os
import asyncio
import configparser
import sys

from random import randint

from iotc.models import Property,Command

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "samples.ini"))

if config["DEFAULT"].getboolean("Local"):
    sys.path.insert(0, "src")

from iotc import (
    IOTCConnectType,
    IOTCLogLevel,
    IOTCEvents,
    Command,
    CredentialsCache,
    Storage,
)
from iotc.aio import IoTCClient

device_id = config["DEVICE_M3"]["DeviceId"]
scope_id = config["DEVICE_M3"]["ScopeId"]
key = config["DEVICE_M3"]["DeviceKey"]
# hub_name = config["SMARTPHONE"]["HubName"]


class MemStorage(Storage):
    def retrieve(self):
        return None

    def persist(self, credentials):
        # a further option would be updating config file with latest hub name
        return None


# optional model Id for auto-provisioning
try:
    model_id = config["SMARTPHONE"]["ModelId"]
except:
    model_id = None


async def on_props(prop:Property):
    print(f"Received {prop.name}:{prop.value}")
    return True


async def on_commands(command: Command):
    print("Received command {} with value {}".format(command.name, command.value))
    await command.reply()


async def on_enqueued_commands(command:Command):
    print("Received offline command {} with value {}".format(command.name, command.value))


#### change connect type to reflect the used key (device or group)
# client = IoTCClient(
#     device_id,
#     scope_id,
#     IOTCConnectType.IOTC_CONNECT_SYMM_KEY,
#     group_key,
#     storage=MemStorage(),
# )

client = IoTCClient(
    device_id,
    scope_id,
    IOTCConnectType.IOTC_CONNECT_DEVICE_KEY,
    key,
    storage=MemStorage(),
)
if model_id != None:
    client.set_model_id(model_id)

client.set_log_level(IOTCLogLevel.IOTC_LOGGING_ALL)
client.on(IOTCEvents.IOTC_PROPERTIES, on_props)
client.on(IOTCEvents.IOTC_COMMAND, on_commands)
client.on(IOTCEvents.IOTC_ENQUEUED_COMMAND, on_enqueued_commands)

async def main():
    await client.connect()
    await client.send_property({"writeableProp": 50})
    
    while not client.terminated():
        if client.is_connected():
            await client.send_telemetry(
                {
                    "temperature": randint(20, 45)
                },{
                    "$.sub": "firstcomponent"
                }
            )
        await asyncio.sleep(3)

asyncio.run(main())
