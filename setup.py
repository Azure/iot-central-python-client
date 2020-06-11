import setuptools
import sys
import semver

sys.path.insert(0, 'src')
from iotc import __name__

with open("README.md", "r") as fh:
    long_description = fh.read()

version="1.0.0"

setuptools.setup(
    name=__name__,
    version=version,
    author="Luca Druda",
    author_email="ludruda@microsoft.com",
    description="Azure IoT Central device client for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lucadruda/iotc-python-device-client",
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    license="MIT",
    platform="OS Independent",
    keywords="iot,azure,iotcentral",
    classifiers=[
      'License :: OSI Approved :: MIT License',
      'Programming Language :: Python',
      'Programming Language :: Python :: 2',
      'Programming Language :: Python :: 2.7',
      'Programming Language :: Python :: 3',
      'Programming Language :: Python :: 3.8',
    ],
    include_package_data=True,
    install_requires=["azure-iot-device","uuid","hmac","hashlib","base64","json"]
)
