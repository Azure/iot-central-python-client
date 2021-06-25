#!/bin/bash
shopt -s expand_aliases

if [[ -f "$HOME/.bashrc" ]]; then
  source $HOME/.bashrc
fi

rm -rf build/ dist/ src/iotc/iotc_device.egg-info src/iotc/_pycache_ src/iotc/_init_.pyc

TEST=""
if [[ $1 == 'test' ]]; then
  TEST="--repository testpypi"
fi

echo "Run tests..."

python -m pytest src/iotc/test
RESULT=$?
if [[ $RESULT -eq 1 ]]; then
  echo "Python3 tests failed. Exiting ..."
  exit -1
fi

python setup.py sdist bdist_wheel
python -m twine upload $TEST dist/*