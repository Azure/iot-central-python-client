import pytest
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


@pytest.mark.asyncio
async def init_compute_key_tests(mocker, key_type, key, device_id):
    client = IoTCClient(
        device_id,
        "scope_id",
        key_type,
        key,
    )
    spy = mocker.spy(client, "_compute_derived_symmetric_key")
    ProvisioningClient = mocker.patch("iotc.aio.ProvisioningDeviceClient")
    DeviceClient = mocker.patch("iotc.aio.IoTHubDeviceClient")
    provisioning_client_instance = mocker.AsyncMock()
    ProvisioningClient.create_from_symmetric_key.return_value = (
        provisioning_client_instance
    )
    DeviceClient.create_from_connection_string.return_value = mocker.AsyncMock()
    await client.connect()
    await client.disconnect()
    return spy


@pytest.mark.asyncio
async def test_compute_device_key_success(mocker):
    group_key = "r0mxLzPr9gg5DfsaxVhOwKK2+8jEHNclmCeb9iACAyb2A7yHPDrB2/+PTmwnTAetvI6oQkwarWHxYbkIVLybEg=="
    device_id = "pytest"
    device_key = "XLXPHX5ND3KBL0BU9Y4C3ZIg4/oSSv3QlYZ0eBfbQtE="

    spy = await init_compute_key_tests(
        mocker, IOTCConnectType.IOTC_CONNECT_SYMM_KEY, group_key, device_id
    )
    spy.assert_called_once_with(group_key, device_id)
    assert spy.spy_return == device_key


@pytest.mark.asyncio
async def test_compute_device_key_skip(mocker):
    group_key = "r0mxLzPr9gg5DfsaxVhOwKK2+8jEHNclmCeb9iACAyb2A7yHPDrB2/+PTmwnTAetvI6oQkwarWHxYbkIVLybEg=="
    device_id = "pytest"
    device_key = "XLXPHX5ND3KBL0BU9Y4C3ZIg4/oSSv3QlYZ0eBfbQtE="
    spy = await init_compute_key_tests(
        mocker, IOTCConnectType.IOTC_CONNECT_DEVICE_KEY, device_key, device_id
    )
    spy.assert_not_called()


@pytest.mark.asyncio
async def test_compute_device_key_failed(mocker):
    group_key = "r0mxLzPr9gg5DfsaxVhOwKK2+8jEHNclmCeb9iACAyb2A7yHPDrB2/+PTmwnTAetvI6oQkwarWHxYbkIVLybEg=="
    device_id = "pytest"
    device_key = "XLXPHX5ND3KBL0BUg4/oSSv3QlYZ0eBfbQtE="

    spy = await init_compute_key_tests(
        mocker, IOTCConnectType.IOTC_CONNECT_SYMM_KEY, group_key, device_id
    )
    spy.assert_called_once_with(group_key, device_id)
    assert spy.spy_return != device_key