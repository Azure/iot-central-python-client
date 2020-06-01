# Azure IoTCentral Device Tests

## Requirements
Tests are written using pytest and the following plugins that must be installed to run properly: _pytest-mock_ and _pytest-asyncio_ for Python 3.7+ tests with asynchronous APIs.

```Shell
pip install pytest pytest-mock pytest-asyncio
```

## Run Tests
Current test structure includes all basic tests in different folders depending of the Python version to use.

---
+--test  
|&nbsp;&nbsp;&nbsp;&nbsp;+--v2  
|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+--test_basics.py  
|&nbsp;&nbsp;&nbsp;&nbsp;+--v3  
|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+--test_basics.py

---

Python 3.7+
```
python3 -m pytest test/v3
```

Python 2.7+
```
python2 -m pytest test/v2
```

Tests by default parse a configuration file including required credentials. Just create a file called **tests.ini** inside the _test_ folder with a content like this:

```ini
[TESTS]
GroupKey = ....
DeviceKey = ....
DeviceId = ....
ScopeId = ....
AssignedHub = ....
ExpectedHub = ....
```

### Run locally
It is possible to run tests against the local copy of the device client. This is particularly useful when testing patches not yet published upstream.
Just add an entry to the configuration file under the _TESTS_ section
```ini
[TESTS]
Local = yes
```
