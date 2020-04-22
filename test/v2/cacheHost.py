# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.

import sys
import time
import hashlib
import hmac
import base64

file_path = __file__[:len(__file__) - len("cacheHost.py")]
# Update /usr/local/lib/python2.7/site-packages/iotc/__init__.py ?
if 'dont_write_bytecode' in dir(sys):
  import os
  sys.dont_write_bytecode = True
  gIsMicroPython = False
else: # micropython
  gIsMicroPython = True
  file_path = file_path[:len(file_path) - 1] if file_path[len(file_path) - 1:] == "b" else file_path
  sys.path.append(file_path + "../src")

import iotc
from iotc import IOTConnectType, IOTLogLevel
import json

pytest_run = False
def test_LOG_IOTC():
  global pytest_run
  pytest_run = True
  assert iotc.LOG_IOTC("LOGME") == 0

def CALLBACK_(info):
  if info.getPayload() == "{\"number\":1}":
    if info.getTag() == "TAG":
      if info.getStatusCode() == 0:
        if info.getEventName() == "TEST":
          info.setResponse(200, "DONE")
          return 0
  return 1

def test_MAKE_CALLBACK():
  client = { "_events" : { "TEST" : CALLBACK_ } }
  ret = iotc.MAKE_CALLBACK(client, "TEST", "{\"number\":1}", "TAG", 0)

  assert ret != 0
  assert ret.getResponseCode() == 200
  assert ret.getResponseMessage() == "DONE"

def test_quote():
  assert iotc._quote("abc+\\0123\"?%456@def", '~()*!.') == "abc%2B%5C0123%22%3F%25456%40def"

with open(file_path + "config.json", "r") as fh:
  configText = fh.read()
config = json.loads(configText)
assert config["scopeId"] != None and config["masterKey"] != None and config["hostName"] != None

testCounter = 0
eventRaised = False
device = None

def compute_key(secret, regId):
  global gIsMicroPython
  try:
    secret = base64.b64decode(secret)
  except:
    print("ERROR: broken base64 secret => `" + secret + "`")
    sys.exit()

  if gIsMicroPython == False:
    return base64.b64encode(hmac.new(secret, msg=regId.encode('utf8'), digestmod=hashlib.sha256).digest())
  else:
    return base64.b64encode(hmac.new(secret, msg=regId.encode('utf8'), digestmod=hashlib._sha256.sha256).digest())

def test_lifetime():
  global testCounter
  global device
  global eventRaised
  if config["TEST_ID"] == 2:
    keyORcert = config["cert"]
  else:
    keyORcert = compute_key(config["masterKey"], "dev1")

  device = iotc.Device(config["scopeId"], keyORcert, "dev1", config["TEST_ID"]) # 1 / 2 (symm / x509)
  if "modelData" in config:
    assert device.setModelData(config["modelData"]) == 0

  device.setExitOnError(True)
  hostName = None

  def onconnect(info):
    global testCounter
    global eventRaised
    print "PASS = " + str(testCounter)
    if testCounter < 2:
      eventRaised = True
    testCounter = testCounter + 1

  assert device.on("ConnectionStatus", onconnect) == 0
  # assert device.setLogLevel(IOTLogLevel.IOTC_LOGGING_ALL) == 0
  assert device.setDPSEndpoint(config["hostName"]) == 0
  assert device.connect() == 0
  hostName = device.getHostName()

  showCommandWarning = False
  MAX_EXPECTED_TEST_COUNTER = 3
  while testCounter < MAX_EXPECTED_TEST_COUNTER:
    if eventRaised == True:
      eventRaised = False
      if testCounter == 1:
        print "DISCONNECTS"
        assert device.disconnect() == 0
      else:
        print "CONNECTS"
        device = iotc.Device(config["scopeId"], keyORcert, "dev1", config["TEST_ID"]) # 1 / 2 (symm / x509)
        assert device.on("ConnectionStatus", onconnect) == 0
        # assert device.setLogLevel(IOTLogLevel.IOTC_LOGGING_ALL) == 0
        assert device.setDPSEndpoint(config["hostName"]) == 0
        device.connect(hostName)

    device.doNext()

  assert device.disconnect() == 0

if pytest_run == False:
  test_LOG_IOTC()
  test_MAKE_CALLBACK()
  test_quote()
  test_lifetime()