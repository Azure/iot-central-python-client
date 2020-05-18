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