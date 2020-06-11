import sys
import os
import configparser
import time
from random import randint


config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__),'samples.ini'))


if config['DEFAULT'].getboolean('Local'):
    sys.path.insert(0, 'src')

from iotc import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents

# Change config section name to reflect sample.ini
device_id = config['DEVICE_A']['DeviceId']
scope_id = config['DEVICE_A']['ScopeId']
key = config['DEVICE_A']['DeviceKey']

# optional model Id for auto-provisioning
try:
    model_id = config['DEVICE_A']['ModelId']
except:
    model_id = None

def on_props(propName, propValue):
    print(propValue)
    return True


def on_commands(command, ack):
    print(command.name)
    ack(command.name, 'Command received', command.request_id)


# see client.Device documentation above for x509 argument sample
client = IoTCClient(device_id, scope_id,
                  IOTCConnectType.IOTC_CONNECT_DEVICE_KEY, key)
if model_id != None:
    client.set_model_id(model_id)

client.set_log_level(IOTCLogLevel.IOTC_LOGGING_ALL)
client.on(IOTCEvents.IOTC_PROPERTIES, on_props)
client.on(IOTCEvents.IOTC_COMMAND, on_commands)



def main():
    client.connect()
    while client.is_connected():
        client.send_telemetry({
            'accelerometerX': str(randint(20, 45)),
            'accelerometerY': str(randint(20, 45)),
            "accelerometerZ": str(randint(20, 45))
        })
        time.sleep(3)


main()
