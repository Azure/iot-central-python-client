import sys
import asyncio
import pkg_resources
from .. import AbstractClient,IOTCLogLevel, IOTCEvents, IOTCConnectType
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


class ConsoleLogger:
    def __init__(self, log_level):
        self._log_level = log_level

    async def _log(self, message):
        print(message)

    async def info(self, message):
        if self._log_level != IOTCLogLevel.IOTC_LOGGING_DISABLED:
            await self._log(message)

    async def debug(self, message):
        if self._log_level == IOTCLogLevel.IOTC_LOGGING_ALL:
            await self._log(message)

    def set_log_level(self, log_level):
        self._log_level = log_level


class IoTCClient(AbstractClient):
    
    def __init__(self, device_id, scope_id, cred_type, key_or_cert, logger=None):
        AbstractClient.__init__(self,device_id, scope_id, cred_type, key_or_cert)
        if logger is None:
            self._logger = ConsoleLogger(IOTCLogLevel.IOTC_LOGGING_API_ONLY)
        else:
            if hasattr(logger, "info") and hasattr(logger, "debug") and hasattr(logger, "set_log_level"):
                self._logger = logger
            else:
                print("ERROR: Logger object has unsupported format. It must implement the following functions\n\
                    info(message);\ndebug(message);\nset_log_level(message);")
                sys.exit()

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
            method_request = (
                await self._device_client.receive_method_request()
            )
            await self._logger.debug(
                'Received command {}'.format(method_request.name))
            await self._device_client.send_method_response(MethodResponse.create_from_method_request(
                method_request, 200, {
                    'result': True, 'data': 'Command received'}
            ))
            await cmd_cb(method_request, self._cmd_ack)

    async def _on_enqueued_commands(self):
        await self._logger.debug('Setup enqueued commands listener')

        while True:
            try:
                enqueued_cmd_cb = self._events[IOTCEvents.IOTC_ENQUEUED_COMMAND]
            except KeyError:
                await self._logger.debug('Enqueued commands callback not found')
                await asyncio.sleep(10)
                continue
            # Wait for unknown method calls
            c2d = await self._device_client.receive_message()
            c2d_name=c2d.custom_properties['method-name'].split(':')[1]
            await self._logger.debug(
                'Received enqueued command {}'.format(c2d_name))
            await enqueued_cmd_cb(c2d_name,c2d.data)

    async def _send_message(self, payload, properties):
        msg = self._prepare_message(payload,properties)
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
            await self._logger.debug('Device connected')
        except:
            await self._logger.info('ERROR: Failed to connect to Hub')
            sys.exit()

        # setup listeners
        self._prop_thread = asyncio.create_task(self._on_properties())
        self._cmd_thread = asyncio.create_task(self._on_commands())
        self._enqueued_cmd_thread = asyncio.create_task(self._on_enqueued_commands())
        # self._threads = await asyncio.gather(
        #     # self._on_properties(),
        #     self._on_commands(),
        #     # self._on_enqueued_commands()
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
