import sys
import signal
import asyncio
import pkg_resources
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
        self, device_id, scope_id, cred_type, key_or_cert, logger=None, storage=None
    ):
        AbstractClient.__init__(
            self, device_id, scope_id, cred_type, key_or_cert, storage
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
            ret = await callback(property_name, property_value, component_name)
        else:
            ret = True
        if ret:
            if component_name is not None:
                await self._logger.debug("Acknowledging {}".format(property_name))
                await self.send_property(
                    {
                        "{}".format(component_name): {
                            "{}".format(property_name): {
                                "ac": 200,
                                "ad": "Property received",
                                "av": property_version,
                                "value": property_value,
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
                            "ad": "Property received",
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
                is_component = patch[prop]["__t"]
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
                        patch[prop][component_prop]["value"],
                        patch["$version"],
                        prop,
                    )
            else:
                await self._handle_property_ack(
                    prop_cb, prop, patch[prop]["value"], patch["$version"]
                )

    async def _on_properties(self):
        await self._logger.debug("Setup properties listener")
        while not self._terminate:
            try:
                prop_cb = self._events[IOTCEvents.IOTC_PROPERTIES]
            except KeyError:
                # await self._logger.debug("Properties callback not found")
                await asyncio.sleep(0.1)
                continue
            try:
                patch = (
                    await self._device_client.receive_twin_desired_properties_patch()
                )
            except asyncio.CancelledError:
                return
            await self._logger.debug("Received desired properties. {}".format(patch))

            await self._update_properties(patch, prop_cb)
            await asyncio.sleep(0.1)

        await self._logger.debug("Stopping properties listener...")

    async def _cmd_ack(self, name, value, request_id, component_name):
        if component_name is not None:
            await self.send_property(
                {
                    "{}".format(component_name): {
                        "{}".format(name): {"value": value, "requestId": request_id}
                    }
                }
            )
        else:
            await self.send_property(
                {"{}".format(name): {"value": value, "requestId": request_id}}
            )

    async def _on_commands(self):
        await self._logger.debug("Setup commands listener")
        while not self._terminate:
            try:
                cmd_cb = self._events[IOTCEvents.IOTC_COMMAND]
            except KeyError:
                # await self._logger.debug("Commands callback not found")
                await asyncio.sleep(0.1)
                continue
            # Wait for unknown method calls
            try:
                method_request = await self._device_client.receive_method_request()
            except asyncio.CancelledError:
                return
            command = Command(method_request.name, method_request.payload)
            command_name_with_components = method_request.name.split("*")

            if len(command_name_with_components) > 1:
                # In a component
                await self._logger.debug("Command in a component")
                command = Command(
                    command_name_with_components[1],
                    method_request.payload,
                    command_name_with_components[0],
                )

            async def reply_fn():
                await self._device_client.send_method_response(
                    MethodResponse.create_from_method_request(
                        method_request,
                        200,
                        {"result": True, "data": "Command received"},
                    )
                )
                await self._cmd_ack(
                    command.name,
                    command.value,
                    method_request.request_id,
                    command.component_name,
                )

            command.reply = reply_fn
            await self._logger.debug("Received command {}".format(method_request.name))

            await cmd_cb(command)
            await asyncio.sleep(0.1)
        await self._logger.debug("Stopping commands listener...")

    async def _on_enqueued_commands(self):
        await self._logger.debug("Setup enqueued commands listener")
        while not self._terminate:
            try:
                enqueued_cmd_cb = self._events[IOTCEvents.IOTC_ENQUEUED_COMMAND]
            except KeyError:
                await self._logger.debug("Enqueued commands callback not found")
                await asyncio.sleep(0.1)
                continue
            # Wait for unknown method calls
            try:
                c2d = await self._device_client.receive_message()
            except asyncio.CancelledError:
                return
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

            await enqueued_cmd_cb(command)
            await asyncio.sleep(0.1)
        await self._logger.debug("Stopping enqueued commands listener...")

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
        self._terminate = False
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
                    x509 = X509(self._cert_file, self._key_file, self._cert_phrase)
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

            except:
                await self._logger.info(
                    "ERROR: Failed to get device provisioning information"
                )
                sys.exit(1)
        # Connect to iothub
        try:
            print(_credentials.connection_string)
            if self._cred_type in (
                IOTCConnectType.IOTC_CONNECT_DEVICE_KEY,
                IOTCConnectType.IOTC_CONNECT_SYMM_KEY,
            ):
                self._device_client = IoTHubDeviceClient.create_from_connection_string(
                    _credentials.connection_string
                )
            else:
                if 'cert_phrase' in _credentials.certificate:
                    x509 = X509(_credentials.certificate['cert_file'], _credentials.certificate['key_file'], _credentials.certificate['cert_phrase'])
                else:
                    x509 = X509(_credentials.certificate['cert_file'], _credentials.certificate['key_file'])
                self._device_client = IoTHubDeviceClient.create_from_x509_certificate(
                    x509=x509,
                    hostname=_credentials.hub_name,
                    device_id=_credentials.device_id,
                )
            await self._device_client.connect()
            await self._logger.debug("Device connected")
            self._twin = await self._device_client.get_twin()
            await self._logger.debug("Current twin: {}".format(self._twin))
            twin_patch = self._sync_twin()
            if twin_patch is not None:
                await self._update_properties(twin_patch, None)
        except:
            await self._logger.info("ERROR: Failed to connect to Hub")
            if force_dps is True:
                sys.exit(1)
            await self.connect(True)

        # setup listeners
        self._prop_thread = asyncio.create_task(self._on_properties())
        self._cmd_thread = asyncio.create_task(self._on_commands())
        self._enqueued_cmd_thread = asyncio.create_task(self._on_enqueued_commands())
        signal.signal(signal.SIGINT, self.raise_graceful_exit)
        signal.signal(signal.SIGTERM, self.raise_graceful_exit)

    async def disconnect(self):
        await self._logger.info("Received shutdown signal")
        if (
            self._prop_thread is not None
            and self._cmd_thread is not None
            and self._enqueued_cmd_thread is not None
        ):
            tasks = asyncio.gather(
                self._prop_thread, self._cmd_thread, self._enqueued_cmd_thread
            )
        self._terminate = True
        try:
            tasks.cancel()
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
