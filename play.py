import json

obj = {"desired": {"$iotin:settings": {"fanSpeed": {"value": 4}, "ledColor": {
    "value": "red"}}, "$version": 2}, "reported": {"$version": 1}}
version = None
reported = []
if 'desired' in obj:
    obj = obj['desired']
    version = obj['$version']
    for attr, value in obj.items():
        if attr != '$version':
            if not attr.startswith('$iotin:'):
                continue
            ifname = attr
            print("Interface name: `{0}`".format(ifname))
            for propName, propValue in value.items():
                print("PropName:{0}, PropValue:{1}".format(
                    propName, propValue))
                try:
                    eventValue = json.loads(json.dumps(propValue))
                    if version != None:
                        eventValue['sv'] = version
                    prop = {"ifname": ifname, "propName": propName,
                            "eventValue": eventValue}
                    reported.append(prop)
                except:
                    continue

for item in reported:
    ret_code = 200
    ret_message = "completed"
    item["eventValue"]["sc"] = ret_code
    item["eventValue"]["sd"] = ret_message
    patch={}
    prop={"{0}".format(item["propName"]):item["eventValue"]}
    patch[item["ifname"]]=prop
    msg = json.dumps(patch)
    print(msg)
