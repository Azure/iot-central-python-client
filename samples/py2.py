import os
import configparser
import time
from random import randint
from azure.iotcentral.device.client import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents



config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__),'samples.ini'))

device_id = config['SymmetricKey']['DeviceId']
scope_id = config['SymmetricKey']['ScopeId']
key = config['SymmetricKey']['Key']

# optional model Id for auto-provisioning
try:
    model_id = config['SymmetricKey']['ModelId']
except:
    model_id = None

def on_props(propName, propValue):
    print(propValue)
    return True


def on_commands(command, ack):
    print(command.name)
    ack(command.name, 'Command received', command.request_id)


# see iotc.Device documentation above for x509 argument sample
iotc = IoTCClient(device_id, scope_id,
                  IOTCConnectType.IOTC_CONNECT_DEVICE_KEY, key)
if model_id != None:
    iotc.set_model_id(model_id)

iotc.set_log_level(IOTCLogLevel.IOTC_LOGGING_ALL)
iotc.on(IOTCEvents.IOTC_PROPERTIES, on_props)
iotc.on(IOTCEvents.IOTC_COMMAND, on_commands)



def main():
    iotc.connect()
    while iotc.is_connected():
        iotc.send_telemetry({
            'accelerometerX': str(randint(20, 45)),
            'accelerometerY': str(randint(20, 45)),
            "accelerometerZ": str(randint(20, 45))
        })
        time.sleep(3)


main()
