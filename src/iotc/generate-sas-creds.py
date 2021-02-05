from time import time
from urllib.parse import quote_plus
from base64 import decodebytes, encodebytes
from hmac import new as hmac
from hashlib import sha256
from math import floor
import sys
ttl = 21600
assigned_hub = 'iotc-a59da873-2325-495f-ae88-bdce8b1a144d.azure-devices.net'
device_id = 'pippo'
device_key = '+bHSSavb0215fq3hcAN2W3B0hRh2d8oRjqzxpshy6Dc='


def compute_key(key, payload):
    try:
        secret = decodebytes(key.encode('ascii'))
    except:
        print("ERROR: broken base64 secret => `" + key + "`")
        sys.exit()

    ret = encodebytes(hmac(secret, msg=payload.encode(
        'utf8'), digestmod=sha256).digest()).decode('utf-8')
    ret = ret[:-1]
    return ret

expiry = floor(time() + ttl)
resource_uri = '{}/devices/{}'.format(assigned_hub, device_id)
signature = quote_plus(compute_key(
    device_key, '{}\n{}'.format(resource_uri, expiry)))

print('{}/{}/?api-version=2019-03-30;'.format(assigned_hub, device_id) +
      'SharedAccessSignature sr={}&sig={}&se={}'.format(resource_uri, signature, expiry))



