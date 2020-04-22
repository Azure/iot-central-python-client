import sys
import asyncio
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device.aio import ProvisioningDeviceClient
from azure.iot.device import Message, MethodResponse
from datetime import datetime

__version__ = "0.0.1-beta.2"
__name__ = "azure-iotcentral-device-client"


def version():
    print(__version__)


try:
    import hmac
except ImportError:
    print("ERROR: missing dependency `micropython-hmac`")
    sys.exit()

try:
    import hashlib
except ImportError:
    print("ERROR: missing dependency `micropython-hashlib`")
    sys.exit()

try:
    import base64
except ImportError:
    print("ERROR: missing dependency `micropython-base64`")
    sys.exit()

try:
    import json
except ImportError:
    print("ERROR: missing dependency `micropython-json`")
    sys.exit()

try:
    import uuid
except ImportError:
    print("ERROR: missing dependency `micropython-uuid`")
    sys.exit()

gIsMicroPython = ('implementation' in dir(sys)) and ('name' in dir(
    sys.implementation)) and (sys.implementation.name == 'micropython')


class IOTCConnectType:
    IOTC_CONNECT_SYMM_KEY = 1
    IOTC_CONNECT_X509_CERT = 2
    IOTC_CONNECT_DEVICE_KEY = 3


class IOTCProtocol:
    IOTC_PROTOCOL_MQTT = 1
    IOTC_PROTOCOL_AMQP = 2
    IOTC_PROTOCOL_HTTP = 4


class IOTCLogLevel:
    IOTC_LOGGING_DISABLED = 1
    IOTC_LOGGING_API_ONLY = 2
    IOTC_LOGGING_ALL = 16


class IOTCConnectionState:
    IOTC_CONNECTION_EXPIRED_SAS_TOKEN = 1
    IOTC_CONNECTION_DEVICE_DISABLED = 2
    IOTC_CONNECTION_BAD_CREDENTIAL = 4
    IOTC_CONNECTION_RETRY_EXPIRED = 8
    IOTC_CONNECTION_NO_NETWORK = 16
    IOTC_CONNECTION_COMMUNICATION_ERROR = 32
    IOTC_CONNECTION_OK = 64


class IOTCMessageStatus:
    IOTC_MESSAGE_ACCEPTED = 1
    IOTC_MESSAGE_REJECTED = 2
    IOTC_MESSAGE_ABANDONED = 4


class IOTCEvents:
    IOTC_COMMAND = 2,
    IOTC_PROPERTIES = 4,


class ConsoleLogger:
    def __init__(self, logLevel):
        self._logLevel = logLevel

    def _log(self, message):
        print(message)

    def info(self, message):
        if self._logLevel != IOTCLogLevel.IOTC_LOGGING_DISABLED:
            self._log(message)

    def debug(self, message):
        if self._logLevel == IOTCLogLevel.IOTC_LOGGING_ALL:
            self._log(message)

    def setLogLevel(self, logLevel):
        self._logLevel = logLevel


class IoTCClient:
    def __init__(self, deviceId, scopeId, credType, keyOrCert, logger=None):
        self._deviceId = deviceId
        self._scopeId = scopeId
        self._credType = credType
        self._keyORCert = keyOrCert
        self._protocol = IOTCProtocol.IOTC_PROTOCOL_MQTT
        self._connected = False
        self._events = {}
        self._globalEndpoint = "global.azure-devices-provisioning.net"
        if logger is None:
            self._logger = ConsoleLogger(IOTCLogLevel.IOTC_LOGGING_API_ONLY)
        else:
            self._logger = logger

    def isConnected(self):
        if self._connected:
            return True
        else:
            return False

    def setProtocol(self, protocol):
        self._protocol = protocol

    def setGlobalEndpoint(self, endpoint):
        self._globalEndpoint = endpoint

    def setModelId(self, modelId):
        self._modelId = modelId

    def setLogLevel(self, logLevel):
        self._logger.setLogLevel(logLevel)

    def on(self, eventname, callback):
        self._events[eventname] = callback
        return 0

    async def _onProperties(self):
        self._logger.debug('Setup properties listener')
        while True:
            propCb = self._events[IOTCEvents.IOTC_PROPERTIES]
            patch = await self._deviceClient.receive_twin_desired_properties_patch()
            self._logger.debug('Received desired properties. {}'.format(patch))

            if propCb:
                for prop in patch:
                    if prop == '$version':
                        continue

                    ret = await propCb(prop, patch[prop]['value'])
                    if ret:
                        self._logger.debug('Acknowledging {}'.format(prop))
                        await self.sendProperty({
                            '{}'.format(prop): {
                                "value": patch[prop]["value"],
                                'status': 'completed',
                                'desiredVersion': patch['$version'],
                                'message': 'Property received'}
                        })
                    else:
                        self._logger.debug(
                            'Property "{}" unsuccessfully processed'.format(prop))

    async def _onCommands(self):
        self._logger.debug('Setup commands listener')

        async def cmdAck(name, value, requestId):
            await self.sendProperty({
                '{}'.format(name): {
                    'value': value,
                    'requestId': requestId
                }
            })
        while True:
            cmdCb = self._events[IOTCEvents.IOTC_COMMAND]
            # Wait for unknown method calls
            method_request = await self._deviceClient.receive_method_request()
            self._logger.debug(
                'Received command {}'.format(method_request.name))
            await self._deviceClient.send_method_response(MethodResponse.create_from_method_request(
                method_request, 200, {
                    'result': True, 'data': 'Command received'}
            ))

            if cmdCb:
                await cmdCb(method_request, cmdAck)

    async def _sendMessage(self, payload, properties, callback= None):
        msg = Message(payload)
        msg.message_id = uuid.uuid4()
        if bool(properties):
            for prop in properties:
                msg.custom_properties[prop] = properties[prop]
        await self._deviceClient.send_message(msg)
        if callback is not None:
            callback()

    async def sendProperty(self, payload, callback=None):
        self._logger.debug('Sending property {}'.format(json.dumps(payload)))
        await self._deviceClient.patch_twin_reported_properties(payload)
        if callback is not None:
            callback()

    async def sendTelemetry(self, payload, properties=None, callback=None):
        self._logger.info('Sending telemetry message: {}'.format(payload))
        await self._sendMessage(json.dumps(payload), properties, callback)

    async def connect(self):
        if self._credType in (IOTCConnectType.IOTC_CONNECT_DEVICE_KEY, IOTCConnectType.IOTC_CONNECT_SYMM_KEY):
            if self._credType == IOTCConnectType.IOTC_CONNECT_SYMM_KEY:
                self._keyORCert = self._computeDerivedSymmetricKey(
                    self._keyORCert, self._deviceId).decode('UTF-8')
                # self._logger.debug('Device key: {}'.format(devKey))
                # self._keyORCert = devKey
                self._provisioningClient = ProvisioningDeviceClient.create_from_symmetric_key(
                    self._globalEndpoint, self._deviceId, self._scopeId, self._keyORCert)
        else:
            self._keyfile = self._keyORCert["keyfile"]
            self._certfile = self._keyORCert["certfile"]
            # Certificate provisioning
            # self._provisioningClient=ProvisioningDeviceClient.create_from_x509_certificate()

        if self._modelId:
            self._provisioningClient.provisioning_payload = {
                'iotcModelId': self._modelId}
        try:
            registration_result = await self._provisioningClient.register()
            assigned_hub = registration_result.registration_state.assigned_hub
            self._logger.debug(assigned_hub)
            self._hubCString = 'HostName={};DeviceId={};SharedAccessKey={}'.format(
                assigned_hub, self._deviceId, self._keyORCert)
            self._logger.debug(
                'IoTHub Connection string: {}'.format(self._hubCString))
            self._deviceClient = IoTHubDeviceClient.create_from_connection_string(
                self._hubCString)
        except:
            self._logger.info(
                'ERROR: Failed to get device provisioning information')
            sys.exit()
        # Connect to iothub
        try:
            await self._deviceClient.connect()
            self._connected = True
            self._logger.debug('Device connected')
        except:
            self._logger.info('ERROR: Failed to connect to Hub')
            sys.exit()

        # setup listeners
        asyncio.create_task(self._onProperties())
        asyncio.create_task(self._onCommands())

    def _computeDerivedSymmetricKey(self, secret, regId):
        # pylint: disable=no-member
        global gIsMicroPython
        try:
            secret = base64.b64decode(secret)
        except:
            self._logger.debug(
                "ERROR: broken base64 secret => `" + secret + "`")
            sys.exit()

        if gIsMicroPython == False:
            return base64.b64encode(hmac.new(secret, msg=regId.encode('utf8'), digestmod=hashlib.sha256).digest())
        else:
            return base64.b64encode(hmac.new(secret, msg=regId.encode('utf8'), digestmod=hashlib._sha256.sha256).digest())
