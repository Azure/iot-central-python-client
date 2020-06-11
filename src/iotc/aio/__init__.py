import sys
import asyncio
import pkg_resources
from .. import IOTCLogLevel, IOTCEvents, IOTCConnectType
from azure.iot.device import X509, MethodResponse, Message
from azure.iot.device.aio import IoTHubDeviceClient, ProvisioningDeviceClient

__version__ = pkg_resources.get_distribution("iotc").version

try:
    import hmac
except ImportError:
    print("ERROR: missing dependency `hmac`")
    sys.exit()

try:
    import hashlib
except ImportError:
    print("ERROR: missing dependency `hashlib`")
    sys.exit()

try:
    import base64
except ImportError:
    print("ERROR: missing dependency `base64`")
    sys.exit()

try:
    import json
except ImportError:
    print("ERROR: missing dependency `json`")
    sys.exit()

try:
    import uuid
except ImportError:
    print("ERROR: missing dependency `uuid`")
    sys.exit()


__version__ = "0.2.2-beta.1"
__name__ = "iotc"

class ConsoleLogger:
    def __init__(self, log_level):
        self._log_level = log_level

    async def _log(self, message):
        print(message)

    async def info(self, message):
        if self._log_level != IOTCLogLevel.IOTC_LOGGING_DISABLED:
            self._log(message)

    async def debug(self, message):
        if self._log_level == IOTCLogLevel.IOTC_LOGGING_ALL:
            self._log(message)

    def set_log_level(self, log_level):
        self._log_level = log_level


class IoTCClient:
    def __init__(self, device_id, scope_id, cred_type, key_or_cert, logger=None):
        self._device_id = device_id
        self._scope_id = scope_id
        self._cred_type = cred_type
        self._key_or_cert = key_or_cert
        self._model_id = None
        self._connected = False
        self._events = {}
        # self._threads = None
        self._cmd_thread = None
        self._prop_thread = None
        self._global_endpoint = "global.azure-devices-provisioning.net"
        if logger is None:
            self._logger = ConsoleLogger(IOTCLogLevel.IOTC_LOGGING_API_ONLY)
        else:
            if hasattr(logger,"info") and hasattr(logger,"debug") and hasattr(logger,"set_log_level"):
                self._logger = logger
            else:
                print("ERROR: Logger object has unsupported format. It must implement the following functions\n\
                    info(message);\ndebug(message);\nset_log_level(message);")
                sys.exit()

    def is_connected(self):
        """
        Check if device is connected to IoTCentral
        :returns: Connection state
        :rtype: bool
        """
        if self._connected:
            return True
        else:
            return False

    def set_global_endpoint(self, endpoint):
        """
        Set the device provisioning endpoint.
        :param str endpoint: Custom device provisioning endpoint. Default ('global.azure-devices-provisioning.net')
        """
        self._global_endpoint = endpoint

    def set_model_id(self, model_id):
        """
        Set the model Id for the device to be associated
        :param str model_id: Id for an existing model in the IoTCentral app
        """
        self._model_id = model_id

    def set_log_level(self, log_level):
        """
        Set the logging level
        :param IOTClog_level: Logging level. Available options are: ALL, API_ONLY, DISABLE
        """
        self._logger.set_log_level(log_level)

    def on(self, eventname, callback):
        """
        Set a listener for a specific event
        :param IOTCEvents eventname: Supported events: IOTC_PROPERTIES, IOTC_COMMANDS
        :param function callback: Function executed when the specified event occurs
        """
        self._events[eventname] = callback
        return 0

    async def _on_properties(self):
        await self._logger.debug('Setup properties listener')
        while True:
            try:
                prop_cb = self._events[IOTCEvents.IOTC_PROPERTIES]
            except KeyError:
                await self._logger.debug('Properties callback not found')
                await asyncio.sleep(10)
                continue
            patch = await self._device_client.receive_twin_desired_properties_patch()
            await self._logger.debug('Received desired properties. {}'.format(patch))

            for prop in patch:
                if prop == '$version':
                    continue

                ret = await prop_cb(prop, patch[prop]['value'])
                if ret:
                    await self._logger.debug('Acknowledging {}'.format(prop))
                    await self.send_property({
                        '{}'.format(prop): {
                            "value": patch[prop]["value"],
                            'status': 'completed',
                            'desiredVersion': patch['$version'],
                            'message': 'Property received'}
                    })
                else:
                    await self._logger.debug(
                        'Property "{}" unsuccessfully processed'.format(prop))

    async def _cmd_ack(self, name, value, requestId):
        await self.send_property({
            '{}'.format(name): {
                'value': value,
                'requestId': requestId
            }
        })

    async def _on_commands(self):
        await self._logger.debug('Setup commands listener')

        while True:
            try:
                cmd_cb = self._events[IOTCEvents.IOTC_COMMAND]
            except KeyError:
                await self._logger.debug('Commands callback not found')
                await asyncio.sleep(10)
                continue
            # Wait for unknown method calls
            method_request = await self._device_client.receive_method_request()
            await self._logger.debug(
                'Received command {}'.format(method_request.name))
            await self._device_client.send_method_response(MethodResponse.create_from_method_request(
                method_request, 200, {
                    'result': True, 'data': 'Command received'}
            ))
            await cmd_cb(method_request, self._cmd_ack)

    async def _send_message(self, payload, properties):
        msg = Message(payload)
        msg.message_id = uuid.uuid4()
        if bool(properties):
            for prop in properties:
                msg.custom_properties[prop] = properties[prop]
        await self._device_client.send_message(msg)

    async def send_property(self, payload):
        """
        Send a property message
        :param dict payload: The properties payload. Can contain multiple properties in the form {'<propName>':{'value':'<propValue>'}}
        """
        await self._logger.debug('Sending property {}'.format(json.dumps(payload)))
        await self._device_client.patch_twin_reported_properties(payload)

    async def send_telemetry(self, payload, properties=None):
        """
        Send a telemetry message
        :param dict payload: The telemetry payload. Can contain multiple telemetry fields in the form {'<fieldName1>':<fieldValue1>,...,'<fieldNameN>':<fieldValueN>}
        :param dict optional properties: An object with custom properties to add to the message.
        """
        await self._logger.info('Sending telemetry message: {}'.format(payload))
        await self._send_message(json.dumps(payload), properties)

    async def connect(self):
        """
        Connects the device.
        :raises exception: If connection fails
        """
        if self._cred_type in (IOTCConnectType.IOTC_CONNECT_DEVICE_KEY, IOTCConnectType.IOTC_CONNECT_SYMM_KEY):
            if self._cred_type == IOTCConnectType.IOTC_CONNECT_SYMM_KEY:
                self._key_or_cert = await self._compute_derived_symmetric_key(
                    self._key_or_cert, self._device_id)

            await self._logger.debug('Device key: {}'.format(self._key_or_cert))

            self._provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
                self._global_endpoint, self._device_id, self._scope_id, self._key_or_cert)
        else:
            self._key_file = self._key_or_cert['key_file']
            self._cert_file = self._key_or_cert['cert_file']
            try:
                self._cert_phrase = self._key_or_cert['cert_phrase']
                x509 = X509(self._cert_file, self._key_file, self._cert_phrase)
            except:
                await self._logger.debug(
                    'No passphrase available for certificate. Trying without it')
                x509 = X509(self._cert_file, self._key_file)
            # Certificate provisioning
            self._provisioning_client = ProvisioningDeviceClient.create_from_x509_certificate(
                provisioning_host=self._global_endpoint, registration_id=self._device_id, id_scope=self._scope_id, x509=x509)

        if self._model_id:
            self._provisioning_client.provisioning_payload = {
                'iotcmodel_id': self._model_id}
        try:
            registration_result = await self._provisioning_client.register()
            assigned_hub = registration_result.registration_state.assigned_hub
            await self._logger.debug(assigned_hub)
            self._hub_conn_string = 'HostName={};DeviceId={};SharedAccessKey={}'.format(
                assigned_hub, self._device_id, self._key_or_cert)
            await self._logger.debug(
                'IoTHub Connection string: {}'.format(self._hub_conn_string))

            if self._cred_type in (IOTCConnectType.IOTC_CONNECT_DEVICE_KEY, IOTCConnectType.IOTC_CONNECT_SYMM_KEY):
                self._device_client = IoTHubDeviceClient.create_from_connection_string(
                    self._hub_conn_string)
            else:
                self._device_client = IoTHubDeviceClient.create_from_x509_certificate(
                    x509=x509, hostname=assigned_hub, device_id=registration_result.registration_state.device_id)
        except:
            await self._logger.info(
                'ERROR: Failed to get device provisioning information')
            sys.exit()
        # Connect to iothub
        try:
            await self._device_client.connect()
            self._connected = True
            await self._logger.debug('Device connected')
        except:
            await self._logger.info('ERROR: Failed to connect to Hub')
            sys.exit()

        # setup listeners
        self._prop_thread = asyncio.create_task(self._on_properties())
        self._cmd_thread = asyncio.create_task(self._on_commands())
        # self._threads = await asyncio.gather(
        #     self._on_properties(),
        #     self._on_commands()
        # )

    async def _compute_derived_symmetric_key(self, secret, reg_id):
        # pylint: disable=no-member
        try:
            secret = base64.b64decode(secret)
        except:
            await self._logger.debug(
                "ERROR: broken base64 secret => `" + secret + "`")
            sys.exit()

        return base64.b64encode(hmac.new(secret, msg=reg_id.encode('utf8'), digestmod=hashlib.sha256).digest()).decode('utf-8')
