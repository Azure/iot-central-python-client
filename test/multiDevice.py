# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.

import sys
import time
import hashlib
import hmac
import base64

file_path = __file__[:len(__file__) - len("multiDevice.py")]
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
devices = []

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

def test_lifetime(id):
  deviceId = "dev" + str(id + 1)
  devices.append(iotc.Device(config["scopeId"], compute_key(config["masterKey"], deviceId), deviceId, config["TEST_ID"])) # 1 / 2 (symm / x509)
  if "modelData" in config:
    assert devices[id].setModelData(config["modelData"]) == 0

  devices[id].setExitOnError(True)

  def onconnect(info):
    global testCounter
    if devices[id].isConnected():
      assert info.getStatusCode() == 0
      testCounter += 1
      assert devices[id].sendTelemetry("{\"temp\":22}", {"iothub-creation-time-utc": time.time()}) == 0
      testCounter += 1
      assert devices[id].sendProperty("{\"dieNumber\":3}") == 0
    else:
      print ("- ", "done", "device", deviceId)

  def onmessagesent(info):
    global testCounter
    print ("onmessagesent", deviceId, info.getTag(), info.getPayload())
    testCounter += 1

  def oncommand(info):
    global testCounter

    print("oncommand", deviceId, info.getTag(), info.getPayload())
    assert info.getTag() == "echo"
    testCounter += 1

  allSettings = {}

  def onsettingsupdated(info):
    global testCounter
    testCounter += 1
    assert '$version' in json.loads(info.getPayload()) # each setting has a version
    assert not info.getTag() + str(id) in allSettings # no double event
    allSettings[info.getTag() + str(id)] = True
    print("onsettingsupdated", deviceId, info.getTag(), info.getPayload())

  assert devices[id].on("ConnectionStatus", onconnect) == 0
  assert devices[id].on("MessageSent", onmessagesent) == 0
  assert devices[id].on("Command", oncommand) == 0
  assert devices[id].on("SettingsUpdated", onsettingsupdated) == 0

  assert devices[id].setLogLevel(IOTLogLevel.IOTC_LOGGING_ALL) == 0

  assert devices[id].setDPSEndpoint(config["hostName"]) == 0
  assert devices[id].connect() == 0

if pytest_run == False:
  test_LOG_IOTC()
  test_MAKE_CALLBACK()
  test_quote()

  for i in range(3):
    test_lifetime(i)

  while testCounter < 30:
    for i in range(3):
      assert devices[i].isConnected()
      devices[i].doNext()

  for i in range(3):
    assert devices[i].disconnect() == 0
