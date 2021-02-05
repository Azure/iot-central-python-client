import os
import configparser
import sys
from random import randint

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__),'samples.ini'))

# Change config section name to reflect sample.ini
device_id = config['DEVICE_A']['DeviceId']
scope_id = config['DEVICE_A']['ScopeId']
hub_name = config["DEVICE_A"]["HubName"]
x509 = {'cert_file': config['DEVICE_A']['CertFilePath'],'key_file':config['DEVICE_A']['KeyFilePath'],'cert_phrase':config['DEVICE_A']['CertPassphrase']}


if config['DEFAULT'].getboolean('Local'):
    sys.path.insert(0, 'src')

from iotc import IOTCConnectType, IOTCLogLevel, IOTCEvents,IoTCClient


class MemStorage(Storage):
    def retrieve(self):
        return CredentialsCache(
            hub_name,
            device_id,
            certificate=x509,
        )

    def persist(self, credentials):
        # a further option would be updating config file with latest hub name
        return None


# optional model Id for auto-provisioning
try:
    model_id = config["DEVICE_M3"]["ModelId"]
except:
    model_id = None


def on_props(property_name, property_value, component_name):
    print("Received {}:{}".format(property_name, property_value))
    return True


def on_commands(command: Command):
    print("Received command {} with value {}".format(command.name, command.value))
    command.reply()


def on_enqueued_commands(command:Command):
    print("Received offline command {} with value {}".format(command.name, command.value))


# change connect type to reflect the used key (device or group)
client = IoTCClient(
    device_id,
    scope_id,
    IOTCConnectType.IOTC_CONNECT_X509_CERT,
    x509,
    storage=MemStorage(),
)
if model_id != None:
    client.set_model_id(model_id)

client.set_log_level(IOTCLogLevel.IOTC_LOGGING_ALL)
client.on(IOTCEvents.IOTC_PROPERTIES, on_props)
client.on(IOTCEvents.IOTC_COMMAND, on_commands)
client.on(IOTCEvents.IOTC_ENQUEUED_COMMAND, on_enqueued_commands)

def main():
    client.connect()
    client.send_property({"writeableProp": 50})
    
    while client.is_connected():
        print("client connected {}".format(client._device_client.connected))
        client.send_telemetry(
            {
                "acceleration": {
                    "x": str(randint(20, 45)),
                    "y": str(randint(20, 45)),
                    "z": str(randint(20, 45)),
                }
            }
        )
        time.sleep(3)

main()
