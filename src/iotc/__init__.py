
import sys
import threading
import time
import pkg_resources
from azure.iot.device import X509
from azure.iot.device import IoTHubDeviceClient
from azure.iot.device import ProvisioningDeviceClient
from azure.iot.device import Message, MethodResponse
from datetime import datetime

__version__ = pkg_resources.get_distribution("iotc").version
if sys.version_info[0] < 3:
    import urllib
    quote = urllib.quote_plus
else:
    import urllib.parse
    quote = urllib.parse.quote_plus

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



class IOTCConnectType:
    IOTC_CONNECT_SYMM_KEY = 1
    IOTC_CONNECT_X509_CERT = 2
    IOTC_CONNECT_DEVICE_KEY = 3


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
    IOTC_ENQUEUED_COMMAND = 8


class ConsoleLogger:
    def __init__(self, log_level):
        self._log_level = log_level

    def _log(self, message):
        print(message)

    def info(self, message):
        if self._log_level != IOTCLogLevel.IOTC_LOGGING_DISABLED:
            self._log(message)

    def debug(self, message):
        if self._log_level == IOTCLogLevel.IOTC_LOGGING_ALL:
            self._log(message)

    def set_log_level(self, log_level):
        self._log_level = log_level


class AbstractClient:
    def __init__(self, device_id, scope_id, cred_type, key_or_cert):
        self._device_id = device_id
        self._scope_id = scope_id
        self._cred_type = cred_type
        self._key_or_cert = key_or_cert
        self._model_id = None
        self._events = {}
        self._prop_thread = None
        self._cmd_thread = None
        self._enqueued_cmd_thread = None
        self._content_type='application%2Fjson'
        self._content_encoding='utf-8'
        self._global_endpoint = "global.azure-devices-provisioning.net"

    def is_connected(self):
        """
        Check if device is connected to IoTCentral
        :returns: Connection state
        :rtype: bool
        """
        if not self._device_client:
            print("ERROR: A connection was never attempted. You need to first call connect() before querying the connection state")
        else:
            return self._device_client.connected

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
        :param IOTCLogLevel: Logging level. Available options are: ALL, API_ONLY, DISABLE
        """
        self._logger.set_log_level(log_level)

    def set_content_type(self,content_type):
        self._content_type = quote(content_type)

    def set_content_encoding(self,content_encoding):
        self._content_encoding = content_encoding

    def _prepare_message(self,payload,properties):
        msg = Message(payload,uuid.uuid4(),self._content_encoding,self._content_type)
        if bool(properties):
            for prop in properties:
                msg.custom_properties[prop] = properties[prop]
        return msg

    def on(self, eventname, callback):
        """
        Set a listener for a specific event
        :param IOTCEvents eventname: Supported events: IOTC_PROPERTIES, IOTC_COMMANDS
        :param function callback: Function executed when the specified event occurs
        """
        self._events[eventname] = callback
        return 0

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


    def _on_properties(self):
        self._logger.debug('Setup properties listener')
        while True:
            try:
                prop_cb = self._events[IOTCEvents.IOTC_PROPERTIES]
            except KeyError:
                self._logger.debug('Properties callback not found')
                time.sleep(10)
                continue

            patch = self._device_client.receive_twin_desired_properties_patch()
            self._logger.debug(
                '\nReceived desired properties. {}\n'.format(patch))

            for prop in patch:
                if prop == '$version':
                    continue

                ret = prop_cb(prop, patch[prop]['value'])
                if ret:
                    self._logger.debug('Acknowledging {}'.format(prop))
                    self.send_property({
                        '{}'.format(prop): {
                            "value": patch[prop]["value"],
                            'status': 'completed',
                            'desiredVersion': patch['$version'],
                            'message': 'Property received'}
                    })
                else:
                    self._logger.debug(
                        'Property "{}" unsuccessfully processed'.format(prop))

    def _cmd_ack(self, name, value, request_id):
        self.send_property({
            '{}'.format(name): {
                'value': value,
                'requestId': request_id
            }
        })

    def _on_commands(self):
        self._logger.debug('Setup commands listener')
        while True:
            try:
                cmd_cb = self._events[IOTCEvents.IOTC_COMMAND]
            except KeyError:
                self._logger.debug('Commands callback not found')
                time.sleep(10)
                continue
            # Wait for unknown method calls
            method_request = self._device_client.receive_method_request()
            self._logger.debug(
                'Received command {}'.format(method_request.name))
            self._device_client.send_method_response(MethodResponse.create_from_method_request(
                method_request, 200, {
                    'result': True, 'data': 'Command received'}
            ))
            cmd_cb(method_request, self._cmd_ack)

    def _on_enqueued_commands(self):
        self._logger.debug('Setup enqueued commands listener')
        while True:
            try:
                enqueued_cmd_cb = self._events[IOTCEvents.IOTC_ENQUEUED_COMMAND]
            except KeyError:
                self._logger.debug('Enqueued commands callback not found')
                time.sleep(10)
                continue
            # Wait for unknown method calls
            c2d = self._device_client.receive_message()
            c2d_name=c2d.custom_properties['method-name'].split(':')[1]
            self._logger.debug(
                'Received enqueued command {}'.format(c2d_name))
            enqueued_cmd_cb(c2d_name,c2d.data)

    def _send_message(self, payload, properties):
        msg = self._prepare_message(payload,properties)
        self._device_client.send_message(msg)

    def send_property(self, payload):
        """
        Send a property message
        :param dict payload: The properties payload. Can contain multiple properties in the form {'<propName>':{'value':'<propValue>'}}
        """
        self._logger.debug('Sending property {}'.format(json.dumps(payload)))
        self._device_client.patch_twin_reported_properties(payload)

    def send_telemetry(self, payload, properties=None):
        """
        Send a telemetry message
        :param dict payload: The telemetry payload. Can contain multiple telemetry fields in the form {'<fieldName1>':<fieldValue1>,...,'<fieldNameN>':<fieldValueN>}
        :param dict optional properties: An object with custom properties to add to the message.
        """
        self._logger.info('Sending telemetry message: {}'.format(payload))
        self._send_message(json.dumps(payload), properties)

    def connect(self):
        """
        Connects the device.
        :raises exception: If connection fails
        """
        if self._cred_type in (IOTCConnectType.IOTC_CONNECT_DEVICE_KEY, IOTCConnectType.IOTC_CONNECT_SYMM_KEY):
            if self._cred_type == IOTCConnectType.IOTC_CONNECT_SYMM_KEY:
                self._key_or_cert = self._compute_derived_symmetric_key(
                    self._key_or_cert, self._device_id)
                self._logger.debug('Device key: {}'.format(self._key_or_cert))

            self._provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
                self._global_endpoint, self._device_id, self._scope_id, self._key_or_cert)
        else:
            self._key_file = self._key_or_cert['key_file']
            self._cert_file = self._key_or_cert['cert_file']
            try:
                self._cert_phrase = self._key_or_cert['cert_phrase']
                x509 = X509(self._cert_file, self._key_file, self._cert_phrase)
            except:
                self._logger.debug(
                    'No passphrase available for certificate. Trying without it')
                x509 = X509(self._cert_file, self._key_file)
            # Certificate provisioning
            self._provisioning_client = ProvisioningDeviceClient.create_from_x509_certificate(
                provisioning_host=self._global_endpoint, registration_id=self._device_id, id_scope=self._scope_id, x509=x509)

        if self._model_id:
            self._provisioning_client.provisioning_payload = {
                'iotcmodel_id': self._model_id}
        try:
            registration_result = self._provisioning_client.register()
            assigned_hub = registration_result.registration_state.assigned_hub
            self._logger.debug(assigned_hub)
            self._hub_conn_string = 'HostName={};DeviceId={};SharedAccessKey={}'.format(
                assigned_hub, self._device_id, self._key_or_cert)
            self._logger.debug(
                'IoTHub Connection string: {}'.format(self._hub_conn_string))

            if self._cred_type in (IOTCConnectType.IOTC_CONNECT_DEVICE_KEY, IOTCConnectType.IOTC_CONNECT_SYMM_KEY):
                self._device_client = IoTHubDeviceClient.create_from_connection_string(
                    self._hub_conn_string)
            else:
                self._device_client = IoTHubDeviceClient.create_from_x509_certificate(
                    x509=x509, hostname=assigned_hub, device_id=registration_result.registration_state.device_id)
        except:
            t, v, tb = sys.exc_info()
            self._logger.info(
                'ERROR: Failed to get device provisioning information')
            raise t(v)
        # Connect to iothub
        try:
            self._device_client.connect()
            self._logger.debug('Device connected')
        except:
            t, v, tb = sys.exc_info()
            self._logger.info('ERROR: Failed to connect to Hub')
            raise t(v)

        # setup listeners

        self._prop_thread = threading.Thread(target=self._on_properties)
        self._prop_thread.daemon = True
        self._prop_thread.start()

        self._cmd_thread = threading.Thread(target=self._on_commands)
        self._cmd_thread.daemon = True
        self._cmd_thread.start()

        self._enqueued_cmd_thread = threading.Thread(target=self._on_enqueued_commands)
        self._enqueued_cmd_thread.daemon = True
        self._enqueued_cmd_thread.start()

    def _compute_derived_symmetric_key(self, secret, reg_id):
        # pylint: disable=no-member
        try:
            secret = base64.b64decode(secret)
        except:
            self._logger.debug(
                "ERROR: broken base64 secret => `" + secret + "`")
            sys.exit()

        return base64.b64encode(hmac.new(secret, msg=reg_id.encode('utf8'), digestmod=hashlib.sha256).digest()).decode('utf-8')
