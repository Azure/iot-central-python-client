import sys
import threading
import signal
import time
import pkg_resources
from azure.iot.device import X509
from azure.iot.device import IoTHubDeviceClient
from azure.iot.device import ProvisioningDeviceClient
from azure.iot.device import Message, MethodResponse
from datetime import datetime
from .models import Command, CredentialsCache, Property, Storage, GracefulExit

try:
    __version__ = pkg_resources.get_distribution("iotc").version
except:
    pass

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
    IOTC_COMMAND = (2,)
    IOTC_PROPERTIES = (4,)
    IOTC_ENQUEUED_COMMAND = 8


class ConsoleLogger:
    def __init__(self, log_level):
        self._log_level = log_level

    def _log(self, message):
        print(message + "\n")

    def info(self, message):
        if self._log_level != IOTCLogLevel.IOTC_LOGGING_DISABLED:
            self._log(message)

    def debug(self, message):
        if self._log_level == IOTCLogLevel.IOTC_LOGGING_ALL:
            self._log(message)

    def set_log_level(self, log_level):
        self._log_level = log_level


class AbstractClient:
    def __init__(self, device_id, scope_id, cred_type, key_or_cert, storage=None, max_connection_attempts=5):
        self._device_id = device_id
        self._scope_id = scope_id
        self._cred_type = cred_type
        self._key_or_cert = key_or_cert
        self._model_id = None
        self._events = {}
        self._prop_thread = None
        self._cmd_thread = None
        self._enqueued_cmd_thread = None
        self._content_type = "application%2Fjson"
        self._content_encoding = "utf-8"
        self._global_endpoint = "global.azure-devices-provisioning.net"
        self._storage = storage
        self._terminate = False
        self._connecting = False
        self._max_connection_attempts = max_connection_attempts
        self._connection_attempts_count = 0

    def terminated(self):
        return self._terminate

    def is_connected(self):
        """
        Check if device is connected to IoTCentral
        :returns: Connection state
        :rtype: bool
        """
        if self._device_client:
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

    def set_content_type(self, content_type):
        self._content_type = quote(content_type)

    def set_content_encoding(self, content_encoding):
        self._content_encoding = content_encoding

    def _prepare_message(self, payload, properties):
        msg = Message(payload, uuid.uuid4(),
                      self._content_encoding, self._content_type)
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

    def _sync_twin(self):
        try:
            desired = self._twin['desired']
            desired_version = self._twin['desired']['$version']
        except KeyError:
            return
        try:
            reported = self._twin['reported']
        except KeyError:
            return
        patch = {}
        for desired_prop in desired:
            print("Syncing property '{}'".format(desired_prop))
            if desired_prop == '$version':
                continue
            # is a component
            if str(type(desired[desired_prop])) == "<class 'dict'>" and '__t' in desired[desired_prop]:
                desired_prop_component = desired_prop
                for desired_prop_name in desired[desired_prop_component]:
                    if desired_prop_name == "__t":
                        continue
                    has_reported = False
                    try:
                        has_reported = reported[desired_prop_component][desired_prop_name]
                    except KeyError:
                        pass
                    if not has_reported:  # no reported yet. send desired
                        patch[desired_prop_component] = desired[desired_prop_component]
                    # desired is more recent
                    if has_reported and 'av' in has_reported and has_reported['av'] < desired_version:
                        patch[desired_prop_component] = desired[desired_prop_component]
            else:  # default component
                has_reported = False
                try:
                    has_reported = reported[desired_prop]
                except KeyError:
                    pass
                if not has_reported:  # no reported yet. send desired
                    patch[desired_prop] = desired[desired_prop]
                # desired is more recent
                if has_reported and 'av' in has_reported and has_reported['av'] < desired_version:
                    patch[desired_prop] = desired[desired_prop]

        if patch:  # there are desired to ack
            patch['$version'] = desired_version
            return patch
        else:
            return None


class IoTCClient(AbstractClient):
    def __init__(
        self, device_id, scope_id, cred_type, key_or_cert, logger=None, storage=None, max_connection_attempts=5
    ):
        AbstractClient.__init__(
            self, device_id, scope_id, cred_type, key_or_cert, storage, max_connection_attempts
        )
        if logger is None:
            self._logger = ConsoleLogger(IOTCLogLevel.IOTC_LOGGING_API_ONLY)
        else:
            if (
                hasattr(logger, "info")
                and hasattr(logger, "debug")
                and hasattr(logger, "set_log_level")
            ):
                self._logger = logger
            else:
                print(
                    "ERROR: Logger object has unsupported format. It must implement the following functions\n\
                    info(message);\ndebug(message);\nset_log_level(message);"
                )
                sys.exit()

    def _handle_property_ack(
        self,
        callback,
        property_name,
        property_value,
        property_version,
        component_name=None,
    ):
        if callback is not None:
            prop = Property(property_name, property_value, component_name)
            ret = callback(prop)
        else:
            ret = True
        if ret:
            if component_name is not None:
                self._logger.debug("Acknowledging {}".format(property_name))
                self.send_property(
                    {
                        "{}".format(component_name): {
                            "__t": "c",
                            "{}".format(property_name): {
                                "value": property_value,
                                "ac": 200,
                                "ad": "Completed",
                                "av": property_version
                            }
                        }
                    }
                )
            else:
                self._logger.debug("Acknowledging {}".format(property_name))
                self.send_property(
                    {
                        "{}".format(property_name): {
                            "ac": 200,
                            "ad": "Completed",
                            "av": property_version,
                            "value": property_value,
                        }
                    }
                )
        else:
            self._logger.debug(
                'Property "{}" unsuccessfully processed'.format(property_name)
            )

    def _update_properties(self, patch, prop_cb):
        for prop in patch:
            is_component = False
            if prop == "$version":
                continue

            # check if component
            try:
                is_component = str(
                    type(patch[prop])) == "<class 'dict'>" and patch[prop]["__t"]
            except KeyError:
                pass
            if is_component:
                for component_prop in patch[prop]:
                    if component_prop == "__t":
                        continue
                    self._logger.debug(
                        'In component "{}" for property "{}"'.format(
                            prop, component_prop
                        )
                    )
                    self._handle_property_ack(
                        prop_cb,
                        component_prop,
                        patch[prop][component_prop],
                        patch["$version"],
                        prop,
                    )
            else:
                self._handle_property_ack(
                    prop_cb, prop, patch[prop], patch["$version"]
                )

    def _on_properties(self, patch):
        self._logger.debug("Setup properties listener")
        try:
            prop_cb = self._events[IOTCEvents.IOTC_PROPERTIES]
        except KeyError:
            self._logger.debug("Properties callback not found")
            return

        self._update_properties(patch, prop_cb)

    def _on_commands(self, method_request):
        self._logger.debug("Setup commands listener")
        try:
            cmd_cb = self._events[IOTCEvents.IOTC_COMMAND]
        except KeyError:
            self._logger.debug("Command callback not found")
            return
        command = Command(method_request.name, method_request.payload)
        try:
            command_name_with_components = method_request.name.split("*")

            if len(command_name_with_components) > 1:
                # In a component
                self._logger.debug("Command in a component")
                command = Command(
                    command_name_with_components[1],
                    method_request.payload,
                    command_name_with_components[0],
                )
        except:
            pass

        def reply_fn():
            self._device_client.send_method_response(
                MethodResponse.create_from_method_request(
                    method_request,
                    200,
                    {"result": True, "data": "Command received"},
                )
            )

        command.reply = reply_fn
        self._logger.debug("Received command {}".format(method_request.name))
        cmd_cb(command)

    def _on_enqueued_commands(self, c2d):
        self._logger.debug("Setup offline commands listener")
        try:
            c2d_cb = self._events[IOTCEvents.IOTC_ENQUEUED_COMMAND]
        except KeyError:
            self._logger.debug("Command callback not found")
            return

        # Wait for unknown method calls
        c2d_name = c2d.custom_properties["method-name"]
        command = Command(c2d_name, c2d.data)
        try:
            command_name_with_components = c2d_name.split("*")

            if len(command_name_with_components) > 1:
                # In a component
                self._logger.debug("Command in a component")
                command = Command(
                    command_name_with_components[1],
                    c2d.data,
                    command_name_with_components[0],
                )
        except:
            pass

        self._logger.debug("Received offline command {}".format(command.name))
        c2d_cb(command)

    def _send_message(self, payload, properties):
        msg = self._prepare_message(payload, properties)
        self._device_client.send_message(msg)

    def send_property(self, payload):
        """
        Send a property message
        :param dict payload: The properties payload. Can contain multiple properties in the form {'<propName>':{'value':'<propValue>'}}
        """
        self._logger.debug("Sending property {}".format(json.dumps(payload)))
        self._device_client.patch_twin_reported_properties(payload)

    def send_telemetry(self, payload, properties=None):
        """
        Send a telemetry message
        :param dict payload: The telemetry payload. Can contain multiple telemetry fields in the form {'<fieldName1>':<fieldValue1>,...,'<fieldNameN>':<fieldValueN>}
        :param dict optional properties: An object with custom properties to add to the message.
        """
        self._logger.info("Sending telemetry message: {}".format(payload))
        self._send_message(json.dumps(payload), properties)

    def connect(self, force_dps=False):
        """
        Connects the device.
        :raises exception: If connection fails
        """
        if self._connection_attempts_count > self._max_connection_attempts:  # max number of retries. exit
            self._terminate = True
            self._connecting = False
            return
        self._terminate = False
        self._connecting = True

        _credentials = None

        # search for existing credentials in store
        if self._storage is not None and force_dps is False:
            _credentials = self._storage.retrieve()
            self._logger.debug("Found cached credentials")

        # no stored credentials. use dps
        if _credentials is None:
            if self._cred_type in (
                IOTCConnectType.IOTC_CONNECT_DEVICE_KEY,
                IOTCConnectType.IOTC_CONNECT_SYMM_KEY,
            ):
                if self._cred_type == IOTCConnectType.IOTC_CONNECT_SYMM_KEY:
                    self._key_or_cert = self._compute_derived_symmetric_key(
                        self._key_or_cert, self._device_id
                    )
                    self._logger.debug(
                        "Device key: {}".format(self._key_or_cert))

                self._provisioning_client = (
                    ProvisioningDeviceClient.create_from_symmetric_key(
                        self._global_endpoint,
                        self._device_id,
                        self._scope_id,
                        self._key_or_cert,
                    )
                )
            else:
                self._key_file = self._key_or_cert["key_file"]
                self._cert_file = self._key_or_cert["cert_file"]
                try:
                    self._cert_phrase = self._key_or_cert["cert_phrase"]
                    x509 = X509(self._cert_file, self._key_file,
                                self._cert_phrase)
                except:
                    self._logger.debug(
                        "No passphrase available for certificate. Trying without it"
                    )
                    x509 = X509(self._cert_file, self._key_file)
                # Certificate provisioning
                self._provisioning_client = (
                    ProvisioningDeviceClient.create_from_x509_certificate(
                        provisioning_host=self._global_endpoint,
                        registration_id=self._device_id,
                        id_scope=self._scope_id,
                        x509=x509,
                    )
                )

            if self._model_id:
                self._provisioning_client.provisioning_payload = {
                    "iotcModelId": self._model_id
                }
            try:
                registration_result = self._provisioning_client.register()
                assigned_hub = registration_result.registration_state.assigned_hub
                self._logger.debug(assigned_hub)
                _credentials = CredentialsCache(
                    assigned_hub,
                    self._device_id,
                    device_key=self._key_or_cert
                    if self._cred_type
                    in (
                        IOTCConnectType.IOTC_CONNECT_DEVICE_KEY,
                        IOTCConnectType.IOTC_CONNECT_SYMM_KEY,
                    )
                    else None,
                    certificate=self._key_or_cert
                    if self._cred_type == IOTCConnectType.IOTC_CONNECT_X509_CERT
                    else None,
                )
                self._logger.debug(
                    "IoTHub Connection string: {}".format(
                        _credentials.connection_string
                    )
                )
                if self._storage is not None:
                    self._storage.persist(_credentials)

            except:
                t, v, tb = sys.exc_info()
                self._logger.info(
                    "ERROR: Failed to get device provisioning information"
                )
                sys.exit(1)
        # Connect to iothub
        try:
            if self._cred_type in (
                IOTCConnectType.IOTC_CONNECT_DEVICE_KEY,
                IOTCConnectType.IOTC_CONNECT_SYMM_KEY,
            ):
                self._device_client = IoTHubDeviceClient.create_from_connection_string(
                    _credentials.connection_string
                )
            else:
                if 'cert_phrase' in _credentials.certificate:
                    x509 = X509(
                        _credentials.certificate['cert_file'], _credentials.certificate['key_file'], _credentials.certificate['cert_phrase'])
                else:
                    x509 = X509(
                        _credentials.certificate['cert_file'], _credentials.certificate['key_file'])
                self._device_client = IoTHubDeviceClient.create_from_x509_certificate(
                    x509=x509,
                    hostname=_credentials.hub_name,
                    device_id=_credentials.device_id,
                )
            self._device_client.connect()
            self._logger.debug("Device connected")
            self._connecting = False
            self._twin = self._device_client.get_twin()
            self._logger.debug("Current twin: {}".format(self._twin))
            prop_patch = self._sync_twin()
            self._logger.debug("Properties to patch: {}".format(prop_patch))
            if prop_patch is not None:
                self._update_properties(prop_patch, None)
        except:  # connection to hub failed. hub can be down or connection string expired. fallback to dps
            t, v, tb = sys.exc_info()
            self._logger.info("ERROR: Failed to connect to Hub")
            if force_dps is True:  # don't fallback to dps as we already using it for connecting
                sys.exit(1)
            self._connection_attempts_count += 1
            self.connect(True)

        # setup listeners

        self._device_client.on_twin_desired_properties_patch_received = self._on_properties
        self._device_client.on_method_request_received = self._on_commands
        self._device_client.on_message_received = self._on_enqueued_commands

        self._conn_thread = threading.Thread(target=self._on_connection_state)
        self._conn_thread.daemon = True
        self._conn_thread.start()

        signal.signal(signal.SIGINT, self.disconnect)
        signal.signal(signal.SIGTERM, self.disconnect)

    def _on_connection_state(self):
        while not self._terminate:
            if not self._connecting and not self.is_connected():
                self._device_client.shutdown()
                self._device_client = None
                self._connection_attempts_count = 0
                self.connect(True)
            time.sleep(1.0)

    def disconnect(self, *args):
        self._logger.info("Received shutdown signal")
        self._terminate = True

        self._device_client.shutdown()
        self._logger.info("Disconnecting client...")
        self._logger.info("Client disconnected.")
        self._logger.info("See you!")

    def _compute_derived_symmetric_key(self, secret, reg_id):
        # pylint: disable=no-member
        try:
            secret = base64.b64decode(secret)
        except:
            self._logger.debug(
                "ERROR: broken base64 secret => `" + secret + "`")
            sys.exit()

        return base64.b64encode(
            hmac.new(
                secret, msg=reg_id.encode("utf8"), digestmod=hashlib.sha256
            ).digest()
        ).decode("utf-8")
