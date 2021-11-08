import pytest
from iotc.models import CredentialsCache
from iotc.models import Storage


class MemStorage(Storage):
    def __init__(self, initial=None):
        if initial:
            self.creds = initial
        else:
            self.creds = {}

    def persist(self, credentials: CredentialsCache):
        self.creds = credentials.todict()

    def retrieve(self):
        return CredentialsCache.from_dict(self.creds)


def test_storage_persist():
    creds = CredentialsCache('hub_name', 'device_id', 'device_key')
    storage = MemStorage()
    storage.persist(creds)
    assert storage.creds['hub_name'] == creds.hub_name
    assert storage.creds['device_id'] == creds.device_id
    assert storage.creds['device_key'] == creds.device_key


def test_storage_retrieve():
    storage = MemStorage(
        {'hub_name': 'hub_name', 'device_id': 'device_id', 'device_key': 'device_key'})
    creds = storage.retrieve()
    assert creds.hub_name == 'hub_name'
    assert creds.device_id == 'device_id'
    assert creds.device_key == 'device_key'


def test_connection_string():
    storage = MemStorage()
    creds = CredentialsCache('hub_name', 'device_id', 'device_key')
    storage.persist(creds)
    cstring = "HostName=hub_name;DeviceId=device_id;SharedAccessKey=device_key"
    assert cstring == creds.connection_string
    assert (storage.retrieve()).connection_string == cstring
