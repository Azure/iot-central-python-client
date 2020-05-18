import os
import asyncio
import configparser
from azure.iotcentral.device.client.aio import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents
from random import randint

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__),'samples.ini'))

device_id = config['x509']['DeviceId']
scope_id = config['x509']['ScopeId']
key = {'certFile': config['x509']['CertFilePath'],'keyFile':config['x509']['KeyFilePath'],'certPhrase':config['x509']['CertPassphrasePath']}

# optional model Id for auto-provisioning
try:
    model_id = config['x509']['ModelId']
except:
    model_id = None


async def on_props(propName, propValue):
    print(propValue)
    return True


async def on_commands(command, ack):
    print(command.name)
    await ack(command.name, 'Command received', command.request_id)


# change connect type to reflect the used key (device or group)
iotc = IoTCClient(device_id, scope_id,
                  IOTCConnectType.IOTC_CONNECT_X509_CERT, key)
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
