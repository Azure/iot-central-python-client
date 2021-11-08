import sys
import signal
import asyncio
import pkg_resources

from iotc.models import Property
from .. import (
    AbstractClient,
    IOTCLogLevel,
    IOTCEvents,
    IOTCConnectType,
    Command,
    CredentialsCache,
    Storage,
    GracefulExit,
)
from contextlib import suppress
from azure.iot.device.common.transport_exceptions import ConnectionDroppedError
from azure.iot.device import X509, MethodResponse, Message
from azure.iot.device.aio import IoTHubDeviceClient, ProvisioningDeviceClient

try:
    __version__ = pkg_resources.get_distribution("iotc").version
except:
    pass


try:
    import hmac
except ImportError:
    print("ERROR: missing dependency `hmac`")
    sys.exit(3)

try:
    import hashlib
except ImportError:
    print("ERROR: missing dependency `hashlib`")
    sys.exit(3)

try:
    import base64
except ImportError:
    print("ERROR: missing dependency `base64`")
    sys.exit(3)

try:
    import json
except ImportError:
    print("ERROR: missing dependency `json`")
    sys.exit(3)

try:
    import uuid
except ImportError:
    print("ERROR: missing dependency `uuid`")
    sys.exit(3)


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

    def raise_graceful_exit(self, *args):
        async def handle_disconnection():
            await self.disconnect()

        try:
            asyncio.run_coroutine_threadsafe(
                handle_disconnection(), asyncio.get_event_loop()
            )
        except:
            pass

    async def _handle_property_ack(
        self,
        callback,
        property_name,
        property_value,
        property_version,
        component_name=None,
    ):
        if callback is not None:
            prop = Property(property_name, property_value, component_name)
            ret = await callback(prop)
        else:
            ret = True
        if ret:
            if component_name is not None:
                await self._logger.debug("Acknowledging {}".format(property_name))
                await self.send_property(
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
                await self._logger.debug("Acknowledging {}".format(property_name))
                await self.send_property(
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
            await self._logger.debug(
                'Property "{}" unsuccessfully processed'.format(property_name)
            )

    async def _update_properties(self, patch, prop_cb):
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
                    await self._logger.debug(
                        'In component "{}" for property "{}"'.format(
                            prop, component_prop
                        )
                    )
                    await self._handle_property_ack(
                        prop_cb,
                        component_prop,
                        patch[prop][component_prop],
                        patch["$version"],
                        prop,
                    )
            else:
                await self._handle_property_ack(
                    prop_cb, prop, patch[prop], patch["$version"]
                )

    async def _on_properties(self, patch):
        await self._logger.debug("Setup properties listener")
        try:
            prop_cb = self._events[IOTCEvents.IOTC_PROPERTIES]
        except KeyError:
            await self._logger.debug("Properties callback not found")
            return

        await self._update_properties(patch, prop_cb)

    async def _on_commands(self, method_request):
        await self._logger.debug("Setup commands listener")
        try:
            cmd_cb = self._events[IOTCEvents.IOTC_COMMAND]
        except KeyError:
            await self._logger.debug("Command callback not found")
            return
        command = Command(method_request.name, method_request.payload)
        try:
            command_name_with_components = method_request.name.split("*")

            if len(command_name_with_components) > 1:
                # In a component
                await self._logger.debug("Command in a component")
                command = Command(
                    command_name_with_components[1],
                    method_request.payload,
                    command_name_with_components[0],
                )
        except:
            pass

        async def reply_fn():
            await self._device_client.send_method_response(
                MethodResponse.create_from_method_request(
                    method_request,
                    200,
                    {"result": True, "data": "Command received"},
                )
            )

        command.reply = reply_fn
        await self._logger.debug("Received command {}".format(method_request.name))
        await cmd_cb(command)

    async def _on_enqueued_commands(self, c2d):
        await self._logger.debug("Setup offline commands listener")
        try:
            c2d_cb = self._events[IOTCEvents.IOTC_ENQUEUED_COMMAND]
        except KeyError:
            await self._logger.debug("Command callback not found")
            return

        # Wait for unknown method calls
        c2d_name = c2d.custom_properties["method-name"]
        command = Command(c2d_name, c2d.data)
        try:
            command_name_with_components = c2d_name.split("*")

            if len(command_name_with_components) > 1:
                # In a component
                await self._logger.debug("Command in a component")
                command = Command(
                    command_name_with_components[1],
                    c2d.data,
                    command_name_with_components[0],
                )
        except:
            pass

        await self._logger.debug("Received offline command {}".format(command.name))
        await c2d_cb(command)

    async def _send_message(self, payload, properties):
        msg = self._prepare_message(payload, properties)
        await self._device_client.send_message(msg)

    async def send_property(self, payload):
        """
        Send a property message
        :param dict payload: The properties payload. Can contain multiple properties in the form {'<propName>':{'value':'<propValue>'}}
        """
        await self._logger.debug("Sending property {}".format(json.dumps(payload)))
        await self._device_client.patch_twin_reported_properties(payload)

    async def send_telemetry(self, payload, properties=None):
        """
        Send a telemetry message
        :param dict payload: The telemetry payload. Can contain multiple telemetry fields in the form {'<fieldName1>':<fieldValue1>,...,'<fieldNameN>':<fieldValueN>}
        :param dict optional properties: An object with custom properties to add to the message.
        """
        await self._logger.info("Sending telemetry message: {}".format(payload))
        await self._send_message(json.dumps(payload), properties)

    async def connect(self, force_dps=False):
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

        if self._storage is not None and force_dps is False:
            _credentials = self._storage.retrieve()
            await self._logger.debug("Found cached credentials")

        if _credentials is None:
            if self._cred_type in (
                IOTCConnectType.IOTC_CONNECT_DEVICE_KEY,
                IOTCConnectType.IOTC_CONNECT_SYMM_KEY,
            ):
                if self._cred_type == IOTCConnectType.IOTC_CONNECT_SYMM_KEY:
                    self._key_or_cert = await self._compute_derived_symmetric_key(
                        self._key_or_cert, self._device_id
                    )

                await self._logger.debug("Device key: {}".format(self._key_or_cert))

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
                    await self._logger.debug(
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
                print("Provision model Id")
                self._provisioning_client.provisioning_payload = {
                    "iotcModelId": self._model_id
                }
            try:
                registration_result = await self._provisioning_client.register()
                assigned_hub = registration_result.registration_state.assigned_hub
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

                if self._storage is not None:
                    self._storage.persist(_credentials)

            except Exception as e:
                await self._logger.info(
                    "ERROR: Failed to get device provisioning information. {}".format(
                        e)
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
            await self._device_client.connect()
            await self._logger.debug("Device connected to '{}'".format(_credentials.hub_name))
            self._connecting = False
            self._twin = await self._device_client.get_twin()
            await self._logger.debug("Current twin: {}".format(self._twin))
            twin_patch = self._sync_twin()
            if twin_patch is not None:
                await self._update_properties(twin_patch, None)
        except Exception as e:  # connection to hub failed. hub can be down or connection string expired. fallback to dps
            await self._logger.info("ERROR: Failed to connect to Hub. {}".format(e))
            if force_dps is True:
                sys.exit(1)
            self._connection_attempts_count += 1
            await self.connect(True)

        # setup listeners
        self._device_client.on_twin_desired_properties_patch_received = self._on_properties
        self._device_client.on_method_request_received = self._on_commands
        self._device_client.on_message_received = self._on_enqueued_commands

        if hasattr(self, '_conn_thread') and self._conn_thread is not None:
            try:
                self._conn_thread.cancel()
                await self._conn_thread
            except asyncio.CancelledError:
                print("Resetting conn_status thread")
        self._conn_thread = asyncio.create_task(self._on_connection_state())

        signal.signal(signal.SIGINT, self.raise_graceful_exit)
        signal.signal(signal.SIGTERM, self.raise_graceful_exit)

    async def _on_connection_state(self):
        while not self._terminate:
            if not self._connecting and not self.is_connected():
                await self._device_client.shutdown()
                self._device_client = None
                self._connection_attempts_count = 0
                await self.connect(True)
            await asyncio.sleep(1.0)

    async def disconnect(self):
        await self._logger.info("Received shutdown signal")
        self._terminate = True
        if hasattr(self, '_conn_thread') and self._conn_thread is not None:
            tasks = asyncio.gather(
                self._conn_thread
            )
        try:
            await tasks
        except:
            pass
        await self._device_client.shutdown()
        await self._logger.info("Disconnecting client...")
        await self._logger.info("Client disconnected.")
        await self._logger.info("See you!")

    async def _compute_derived_symmetric_key(self, secret, reg_id):
        # pylint: disable=no-member
        try:
            secret = base64.b64decode(secret)
        except:
            await self._logger.debug("ERROR: broken base64 secret => `" + secret + "`")
            sys.exit(2)

        return base64.b64encode(
            hmac.new(
                secret, msg=reg_id.encode("utf8"), digestmod=hashlib.sha256
            ).digest()
        ).decode("utf-8")
