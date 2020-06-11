#!/bin/bash
shopt -s expand_aliases

if [ -f "~/.bashrc" ]; then
  source ~/.bashrc
fi

rm -rf build/ dist/ src/iotc/iotc_device.egg-info src/iotc/_pycache_ src/iotc/_init_.pyc

TEST=""
if [[ $1 == 'test' ]]; then
  TEST="--repository testpypi"
fi

echo "Run tests..."

python2 -m pytest test/v2
RESULT=$?
if [[ $RESULT -eq 1 ]]; then
  echo "Python2 tests failed. Exiting ..."
  exit -1
fi

python3 -m pytest test/v3
RESULT=$?
if [[ $RESULT -eq 1 ]]; then
  echo "Python3 tests failed. Exiting ..."
  exit -1
fi

python2 setup.py sdist bdist_wheel
python3 setup.py sdist bdist_wheel
python2 -m twine upload $TEST dist/*
python3 -m twine upload $TEST dist/*