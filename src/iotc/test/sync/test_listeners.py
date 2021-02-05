import pytest
import configparser
import os
import time
import sys

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "../tests.ini"))

if config["TESTS"].getboolean("Local"):
    sys.path.insert(0, "src")

from azure.iot.device import MethodRequest, Message
from iotc import IOTCConnectType, IOTCLogLevel, IOTCEvents, IoTCClient,Command
from iotc.test import dummy_storage


DEFAULT_COMPONENT_PROP = {"prop1": {"value": "value1"}, "$version": 1}
COMPONENT_PROP = {
    "component1": {"__t": "c", "prop1": {"value": "value1"}},
    "$version": 1,
}
COMPLEX_COMPONENT_PROP = {
    "component1": {"__t": "c", "prop1": {"value": "value1"}},
    "component2": {
        "__t": "c",
        "prop1": {"value": "value1"},
        "prop2": {"value": "value2"},
    },
    "prop2": {"value": "value2"},
    "$version": 1,
}

DEFAULT_COMMAND = MethodRequest(1, "cmd1", "sample")
COMPONENT_COMMAND = MethodRequest(1, "commandComponent*cmd1", "sample")
COMPONENT_ENQUEUED = Message("sample_data")
COMPONENT_ENQUEUED.custom_properties = {"method-name": "component*command_name"}
DEFAULT_COMPONENT_ENQUEUED = Message("sample_data")
DEFAULT_COMPONENT_ENQUEUED.custom_properties = {"method-name": "command_name"}


def command_equals(self, other):
    return (
        self.name == other.name
        and self.component_name == other.component_name
        and self.value == other.value
    )


Command.__eq__ = command_equals

@pytest.fixture()
def iotc_client(mocker):
    ProvisioningClient = mocker.patch("iotc.ProvisioningDeviceClient")
    DeviceClient = mocker.patch("iotc.IoTHubDeviceClient")
    ProvisioningClient.create_from_symmetric_key.return_value = mocker.MagicMock()
    device_client_instance = (
        DeviceClient.create_from_connection_string.return_value
    ) = mocker.MagicMock()
    mocked_client = IoTCClient(
        "device_id",
        "scope_id",
        IOTCConnectType.IOTC_CONNECT_DEVICE_KEY,
        "device_key_base64",
    )
    mocked_client.set_log_level(IOTCLogLevel.IOTC_LOGGING_ALL)
    mocked_client._device_client = device_client_instance
    yield mocked_client
    try:
        mocked_client.disconnect()
    except asyncio.CancelledError:
        pass


def test_on_properties_triggered(mocker, iotc_client):
    prop_stub = mocker.MagicMock()
    iotc_client.on(IOTCEvents.IOTC_PROPERTIES, prop_stub)
    iotc_client._device_client.receive_twin_desired_properties_patch.return_value = (
        DEFAULT_COMPONENT_PROP
    )
    iotc_client.connect()
    time.sleep(0.1)
    prop_stub.assert_called_with("prop1", "value1", None)



def test_on_properties_triggered_with_component(mocker, iotc_client):
    prop_stub = mocker.MagicMock()
    # set return value, otherwise a check for the function result will execute a mock again
    prop_stub.return_value = True
    iotc_client.on(IOTCEvents.IOTC_PROPERTIES, prop_stub)
    iotc_client._device_client.receive_twin_desired_properties_patch.return_value = (
        COMPONENT_PROP
    )
    iotc_client.connect()
    time.sleep(0.1)
    prop_stub.assert_called_with("prop1", "value1", "component1")



def test_on_properties_triggered_with_complex_component(mocker, iotc_client):
    prop_stub = mocker.MagicMock()
    # set return value, otherwise a check for the function result will execute a mock again
    prop_stub.return_value = True
    iotc_client.on(IOTCEvents.IOTC_PROPERTIES, prop_stub)
    iotc_client._device_client.receive_twin_desired_properties_patch.return_value = (
        COMPLEX_COMPONENT_PROP
    )
    iotc_client.connect()
    time.sleep(0.1)
    prop_stub.assert_has_calls(
        [
            mocker.call("prop1", "value1", "component1"),
            mocker.call("prop1", "value1", "component2"),
            mocker.call("prop2", "value2", "component2"),
            mocker.call("prop2", "value2", None),
        ],any_order=True
    )



def test_on_command_triggered(mocker, iotc_client):
    cmd_stub = mocker.MagicMock()
    iotc_client.on(IOTCEvents.IOTC_COMMAND, cmd_stub)
    iotc_client._device_client.receive_method_request.return_value = DEFAULT_COMMAND
    iotc_client.connect()
    time.sleep(0.1)
    cmd_stub.assert_called_with(Command("cmd1", "sample", None))



def test_on_command_triggered_with_component(mocker, iotc_client):
    cmd_stub = mocker.MagicMock()
    iotc_client.on(IOTCEvents.IOTC_COMMAND, cmd_stub)
    iotc_client._device_client.receive_method_request.return_value = COMPONENT_COMMAND
    iotc_client.connect()
    time.sleep(0.1)
    cmd_stub.assert_called_with(Command("cmd1", "sample", "commandComponent"))



def test_on_enqueued_command_triggered(mocker, iotc_client):
    cmd_stub = mocker.MagicMock()
    iotc_client.on(IOTCEvents.IOTC_ENQUEUED_COMMAND, cmd_stub)
    iotc_client._device_client.receive_message.return_value = DEFAULT_COMPONENT_ENQUEUED
    iotc_client.connect()
    time.sleep(0.1)
    cmd_stub.assert_called_with(Command("command_name", "sample_data", None))



def test_on_enqueued_command_triggered_with_component(mocker, iotc_client):
    cmd_stub = mocker.MagicMock()
    iotc_client.on(IOTCEvents.IOTC_ENQUEUED_COMMAND, cmd_stub)
    iotc_client._device_client.receive_message.return_value = COMPONENT_ENQUEUED
    iotc_client.connect()
    time.sleep(0.1)
    cmd_stub.assert_called_with(Command("command_name", "sample_data", "component"))
