import sys
import os
import asyncio
import configparser
import logging
import logging.handlers
from random import randint

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'samples.ini'))

if config['DEFAULT'].getboolean('Local'):
    sys.path.insert(0, 'src')

from iotc import IOTCConnectType, IOTCLogLevel, IOTCEvents
from iotc.aio import IoTCClient

device_id = config['SymmetricKey']['DeviceId']
scope_id = config['SymmetricKey']['ScopeId']
key = config['SymmetricKey']['Key']

logpath = config['FileLog']['LogsPath']

# optional model Id for auto-provisioning
try:
    model_id = config['SymmetricKey']['ModelId']
except:
    model_id = None


class FileLogger:
    def __init__(self,logpath,logname="iotc_py_log"):
        self._logger=logging.getLogger(logname)
        self._logger.setLevel(logging.DEBUG)
        handler= logging.handlers.RotatingFileHandler(
              os.path.join(logpath,logname), maxBytes=20, backupCount=5)
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


async def on_props(propName, propValue):
    print(propValue)
    return True


async def on_commands(command, ack):
    print(command.name)
    await ack(command.name, 'Command received', command.request_id)


# change connect type to reflect the used key (device or group)
iotc = IoTCClient(device_id, scope_id,
                  IOTCConnectType.IOTC_CONNECT_DEVICE_KEY, key, FileLogger(logpath))
if model_id != None:
    iotc.set_model_id(model_id)

iotc.set_log_level(IOTCLogLevel.IOTC_LOGGING_ALL)
iotc.on(IOTCEvents.IOTC_PROPERTIES, on_props)
iotc.on(IOTCEvents.IOTC_COMMAND, on_commands)

# iotc.setQosLevel(IOTQosLevel.IOTC_QOS_AT_MOST_ONCE)


async def main():
    await iotc.connect()
    while iotc.is_connected():
        await iotc.send_telemetry({
            'accelerometerX': str(randint(20, 45)),
            'accelerometerY': str(randint(20, 45)),
            "accelerometerZ": str(randint(20, 45))
        })
        await asyncio.sleep(3)


asyncio.run(main())
