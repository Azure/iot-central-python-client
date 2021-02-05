import pytest
import configparser
import os
import sys

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "../tests.ini"))

if config["TESTS"].getboolean("Local"):
    sys.path.insert(0, "src")

from iotc import IOTCConnectType, IOTCLogLevel, IOTCEvents, IoTCClient
from iotc.test import dummy_storage


@pytest.fixture()
def iotc_client(mocker):
    ProvisioningClient = mocker.patch("iotc.ProvisioningDeviceClient")
    DeviceClient = mocker.patch("iotc.IoTHubDeviceClient")
    provisioning_client_instance = (
        ProvisioningClient.create_from_symmetric_key.return_value
    ) = mocker.MagicMock()
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
    mocked_client._provisioning_client = provisioning_client_instance
    yield mocked_client
    mocked_client.disconnect()



def test_connect_succeeds(iotc_client):
    iotc_client.connect()



def test_dps_connect_failed(iotc_client):
    iotc_client._provisioning_client.register.return_value = None
    with pytest.raises(SystemExit):
        iotc_client.connect()



def test_connect_force_dps(mocker, iotc_client):
    iotc_client._storage = dummy_storage()
    spy = mocker.spy(iotc_client, "connect")
    iotc_client.connect()
    iotc_client.disconnect()
    assert spy.call_count == 2
    assert iotc_client.connect.mock_calls == [mocker.call(), mocker.call(True)]
