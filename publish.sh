#!/bin/bash
shopt -s expand_aliases
source ~/.bashrc

rm -rf build/ dist/ src/azure/iotcentral/device/client/iotc_device.egg-info src/azure/iotcentral/device/client/_pycache_ src/azure/iotcentral/device/client/_init_.pyc

TEST=""
if [[ $1 == 'test' ]]; then
  TEST="--repository testpypi"
fi


#python2 setup.py sdist bdist_wheel
python3 setup.py sdist bdist_wheel
python3 -m twine upload $TEST dist/*