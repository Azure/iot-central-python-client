import os
import sys
file_path = __file__[:len(__file__) - len("basics.py")]
file_path = file_path[:len(file_path) - 1] if file_path[len(file_path) - 1:] == "b" else file_path
sys.path.append(os.path.join(file_path, "..", "src"))

import iotc
from iotc import IOTConnectType, IOTLogLevel, IOTQosLevel
from datetime import datetime, timezone
from threading import Timer, Thread, Event 

class PT():
    def __init__(self, t, hFunction):
        self.t = t
        self.hFunction = hFunction
        self.thread = Timer(self.t, self.handle_function)

    def handle_function(self):
        self.hFunction()
        self.thread = Timer(self.t, self.handle_function)
        self.thread.start()

    def start(self):
        self.thread.start()

deviceId = "<Add device Id here>"
scopeId = "<Add scope Id here>"
deviceKey = "<Add device Key here>"

# see iotc.Device documentation above for x509 argument sample
iotc = iotc.Device(scopeId, deviceKey, deviceId, IOTConnectType.IOTC_CONNECT_SYMM_KEY)
iotc.setLogLevel(IOTLogLevel.IOTC_LOGGING_API_ONLY)
iotc.setTokenExpiration(21600 * 12)

# set QoS level to guarantee delivery at least once
iotc.setQosLevel(IOTQosLevel.IOTC_QOS_AT_LEAST_ONCE)

gCanSend = False
sent = 0
confirmed = 0
enableLogging = False

def log(s):
  if enableLogging:
    f=open("python-iotc.txt","a+")
    f.write(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + " - " + s + "\n")
    f.close()

def onconnect(info):
  global gCanSend
  log("[onconnect] => status:" + str(info.getStatusCode()))
  if info.getStatusCode() == 0:
     if iotc.isConnected():
       gCanSend = True

def onmessagesent(info):
  global confirmed 
  confirmed += 1
  log("[onmessagesent] => " + str(info.getPayload()))

def oncommand(info):
  log("command name:", info.getTag())
  log("command value: ", info.getPayload())

def onsettingsupdated(info):
  log("setting name:", info.getTag())
  log("setting value: ", info.getPayload())

def send():
  global sent
  sent += 1
  print("Sending telemetry.. sent:{}, confirmed: {}".format(sent, confirmed))
  iotc.sendTelemetry("{\"index\": " + str(sent) + "}")

iotc.on("ConnectionStatus", onconnect)
iotc.on("MessageSent", onmessagesent)
iotc.on("Command", oncommand)
iotc.on("SettingsUpdated", onsettingsupdated)
iotc.connect()

t = PT(5, send)
t.start()
