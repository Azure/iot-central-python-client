import sys
sys.path.insert(0, 'src')

from azure.iotcentral.device.client import IoTCClient, IOTCConnectType, IOTCLogLevel, IOTCEvents


groupKey='68p6zEjwVNB6L/Dz8Wkz4VhaTrYqkndPrB0uJbWr2Hc/AmB+Qxz/eJJ9MIhLZFJ6hC0RmHMgfaYBkNTq84OCNQ=='
deviceKey='Jdj7TBhH5RXCD+24bT5PTGf0NwdDbDvsI+rniK2AUHk='
deviceId='nuovodev'
scopeId='0ne00052362'

iotc = IoTCClient(deviceId, scopeId,
                IOTCConnectType.IOTC_CONNECT_SYMM_KEY, groupKey)


def test_properties():
    propName='prop1'
    propValue='val1'

    def onProps(name,value):
        assert propName == name
        assert propValue == value
    
    
    iotc.on(IOTCEvents.IOTC_PROPERTIES,onProps)

    iotc._events[IOTCEvents.IOTC_PROPERTIES](propName,propValue)



def test_commands():
    commandName='cmd1'
    commandValue='val1'

    def onCommand(name,value):
        assert commandName == name
        assert commandValue == value
    
    
    iotc.on(IOTCEvents.IOTC_COMMAND,onCommand)

    iotc._events[IOTCEvents.IOTC_COMMAND](commandName,commandValue)
