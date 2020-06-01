#!/bin/bash
shopt -s expand_aliases
source ~/.bashrc

rm -rf build/ dist/ src/iotc/iotc_device.egg-info src/iotc/_pycache_ src/iotc/_init_.pyc

TEST=""
if [[ $1 == 'test' ]]; then
  TEST="--repository testpypi"
fi


#python2 setup.py sdist bdist_wheel
python3 setup.py sdist bdist_wheel
python3 -m twine upload $TEST dist/*