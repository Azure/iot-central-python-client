class CONSTANTS:
    DEVICE_CAPABILITIES_MESSAGE = "devices/{}/messages/events/%24.ifid=urn%3aazureiot%3aModelDiscovery%3aModelInformation%3a1&%24.ifname=urn_azureiot_ModelDiscovery_ModelInformation&%24.schema=modelInformation&%24.ct=application%2fjson"
    DEVICETWIN_PATCH_MESSAGE="$iothub/twin/PATCH/properties/reported/?$rid={}"
    SDK_VERSION="iotc-python-device-client/0.3.5"
    SDK_VENDOR="Microsoft Corporation"
    MODEL_INFORMATION_KEY="modelInformation"
    INTERFACES_KEY="interfaces"
    CAPABILITY_MODEL_KEY="capabilityModelId"
    DPS_API_VERSION="2019-03-31"
    HUB_API_VERSION="2019-07-01-preview"

    # Interfaces
    INTERFACE_NAME="$.ifname"
    INTERFACE_ID="$.ifid"
    CONTENT_TYPE="$.ct"
    CONTENT_ENCODING="$.ce"

    # Telemetry
    TELEMETRY_SCHEMA="$.schema"

    # Commands
    COMMAND_SCHEMA="iothub-message-schema"
    COMMAND_NAME="iothub-command-name"
    COMMAND_REQUEST_ID="iothub-command-request-id"
    COMMAND_STATUS_CODE="iothub-command-statuscode"
