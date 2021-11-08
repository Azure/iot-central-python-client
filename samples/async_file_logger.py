from iotc.models import Command, Property, CredentialsCache, Storage
from iotc.aio import IoTCClient
from iotc import (
    IOTCConnectType,
    IOTCLogLevel,
    IOTCEvents,
)
import os
import asyncio
import configparser
import sys
import logging

from random import randint

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "samples.ini"))

if config["DEFAULT"].getboolean("Local"):
    sys.path.insert(0, "src")


class FileLogger:
    def __init__(self, logpath, logname="iotc_py_log"):
        self._logger = logging.getLogger(logname)
        self._logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(
            os.path.join(logpath, logname), maxBytes=20, backupCount=5)
        self._logger.addHandler(handler)

    async def _log(self, message):
        print(message)
        self._logger.debug(message)

    async def info(self, message):
        if self._log_level != IOTCLogLevel.IOTC_LOGGING_DISABLED:
            await self._log(message)

    async def debug(self, message):
        if self._log_level == IOTCLogLevel.IOTC_LOGGING_ALL:
            await self._log(message)

    def set_log_level(self, log_level):
        self._log_level = log_level


device_id = config["DEVICE_M3"]["DeviceId"]
scope_id = config["DEVICE_M3"]["ScopeId"]
key = config["DEVICE_M3"]["DeviceKey"]
hub_name = config["DEVICE_M3"]["HubName"]
log_path = config['FileLog']['LogsPath']


class MemStorage(Storage):
    def retrieve(self):
        return CredentialsCache(
            hub_name,
            device_id,
            key,
        )

    def persist(self, credentials):
        # a further option would be updating config file with latest hub name
        return None


# optional model Id for auto-provisioning
try:
    model_id = config["DEVICE_M3"]["ModelId"]
except:
    model_id = None


async def on_props(prop: Property):
    print(f"Received {prop.name}:{prop.value}")
    return True


async def on_commands(command: Command):
    print("Received command {} with value {}".format(command.name, command.value))
    await command.reply()


async def on_enqueued_commands(command: Command):
    print("Received offline command {} with value {}".format(
        command.name, command.value))


# change connect type to reflect the used key (device or group)
client = IoTCClient(
    device_id,
    scope_id,
    IOTCConnectType.IOTC_CONNECT_DEVICE_KEY,
    key,
    logger=FileLogger(log_path),
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
                }, {
                    "$.sub": "firstcomponent"
                }
            )
        await asyncio.sleep(3)

asyncio.run(main())
