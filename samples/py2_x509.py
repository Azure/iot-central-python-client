import sys
sys.path.insert(0, '../src')

import time
from random import randint
from azure.iotcentral.device.client import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents



deviceId = "<DEVICE_ID>"
scopeId = "<SCOPE_ID>"
key = {'certFile':'<CERT_CHAIN_FILE_PATH>','keyFile':'<CERT_KEY_FILE_PATH>','certPhrase':'<CERT_PASSWORD>'}

# optional model Id for auto-provisioning
modelId= '<MODEL_ID>'


def onProps(propName, propValue):
    print(propValue)
    return True


def onCommands(command, ack):
    print(command.name)
    ack(command.name, 'Command received', command.request_id)


# see iotc.Device documentation above for x509 argument sample
iotc = IoTCClient(deviceId, scopeId,
                  IOTCConnectType.IOTC_CONNECT_X509_CERT, key)
iotc.setModelId(modelId)
iotc.setLogLevel(IOTCLogLevel.IOTC_LOGGING_ALL)
iotc.on(IOTCEvents.IOTC_PROPERTIES, onProps)
# iotc.on(IOTCEvents.IOTC_COMMAND, onCommands)



def main():
    iotc.connect()
    while iotc.isConnected():
        iotc.sendTelemetry({
            'accelerometerX': str(randint(20, 45)),
            'accelerometerY': str(randint(20, 45)),
            "accelerometerZ": str(randint(20, 45))
        })
        time.sleep(3)


main()
