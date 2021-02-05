import pytest
import time
import asyncio
import configparser
import os
import sys

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "../tests.ini"))

if config["TESTS"].getboolean("Local"):
    sys.path.insert(0, "src")

from iotc import IOTCConnectType, IOTCLogLevel, IOTCEvents
from iotc.aio import IoTCClient
from iotc.test import dummy_storage


@pytest.fixture()
@pytest.mark.asyncio
async def iotc_client(mocker):
    ProvisioningClient = mocker.patch("iotc.aio.ProvisioningDeviceClient")
    DeviceClient = mocker.patch("iotc.aio.IoTHubDeviceClient")
    provisioning_client_instance = (
        ProvisioningClient.create_from_symmetric_key.return_value
    ) = mocker.AsyncMock()
    device_client_instance = (
        DeviceClient.create_from_connection_string.return_value
    ) = mocker.AsyncMock()
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
    try:
        await mocked_client.disconnect()
    except asyncio.CancelledError:
        pass
    except SystemExit as e:
        if e.code == 1:
            pass


@pytest.mark.asyncio
async def test_connect_succeeds(iotc_client):
    await iotc_client.connect()


@pytest.mark.asyncio
async def test_dps_connect_failed(iotc_client):
    iotc_client._provisioning_client.register.return_value = None
    with pytest.raises(SystemExit):
        await iotc_client.connect()


@pytest.mark.asyncio
async def test_connect_force_dps(mocker, iotc_client):
    iotc_client._storage = dummy_storage()
    spy = mocker.spy(iotc_client, "connect")
    await iotc_client.connect()
    await iotc_client.disconnect()
    assert spy.call_count == 2
    assert iotc_client.connect.mock_calls == [mocker.call(), mocker.call(True)]
