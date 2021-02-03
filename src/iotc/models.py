import abc


class GracefulExit(SystemExit):
    code = 1


class CredentialsCache(object):
    def __init__(self, hub_name, device_id, device_key=None, certificate=None):
        self._hub_name = hub_name
        self._device_id = device_id
        self._device_key = device_key
        self._certificate = certificate

    @property
    def hub_name(self):
        return self._hub_name

    @property
    def device_id(self):
        return self._device_id

    @property
    def device_key(self):
        return self._device_key

    @property
    def certificate(self):
        return self._certificate

    @property
    def connection_string(self):
        if self._hub_name is None or self._device_id is None:
            return None
        elif self._device_key is not None:
            return "HostName={};DeviceId={};SharedAccessKey={}".format(
                self._hub_name, self._device_id, self._device_key
            )
        elif self._certificate is not None:
            return "HostName={};DeviceId={};x509=true".format(
                self._hub_name, self._device_id
            )


class Storage(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def persist(self, credentials):
        pass

    @abc.abstractmethod
    def retrieve(self):
        pass


class Command(object):
    def __init__(self, command_name, command_value, component_name=None):
        self._command_name = command_name
        self._command_value = command_value
        if component_name is not None:
            self._component_name = component_name
        else:
            self._component_name = None
        self.reply = None

    @property
    def name(self):
        return self._command_name

    @property
    def value(self):
        return self._command_value

    @property
    def component_name(self):
        return self._component_name
