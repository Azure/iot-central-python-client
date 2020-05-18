import os
import configparser
import time
from random import randint
from azure.iotcentral.device.client import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__),'samples.ini'))

device_id = config['x509']['DeviceId']
scope_id = config['x509']['ScopeId']
key = {'certFile': config['x509']['CertFilePath'],'keyFile':config['x509']['KeyFilePath'],'certPhrase':config['x509']['CertPassphrase']}

# optional model Id for auto-provisioning
try:
    model_id = config['x509']['ModelId']
except:
    model_id = None


def onProps(propName, propValue):
    print(propValue)
    return True


def onCommands(command, ack):
    print(command.name)
    ack(command.name, 'Command received', command.request_id)


# see iotc.Device documentation above for x509 argument sample
iotc = IoTCClient(device_id, scope_id,
                  IOTCConnectType.IOTC_CONNECT_X509_CERT, key)
iotc.set_model_id(model_id)
iotc.set_log_level(IOTCLogLevel.IOTC_LOGGING_ALL)
iotc.on(IOTCEvents.IOTC_PROPERTIES, onProps)
iotc.on(IOTCEvents.IOTC_COMMAND, onCommands)



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
