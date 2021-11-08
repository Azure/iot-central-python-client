import setuptools
import sys


with open("README.md", "r") as fh:
    long_description = fh.read()

version = "1.1.2"

setuptools.setup(
    name='iotc',
    version=version,
    author="Luca Druda",
    author_email="ludruda@microsoft.com",
    description="Azure IoT Central device client for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/iot-for-all/iotc-python-client",
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    license="MIT",
    platform="OS Independent",
    keywords="iot,azure,iotcentral",
    classifiers=[
      'License :: OSI Approved :: MIT License',
      'Programming Language :: Python',
      'Programming Language :: Python :: 3',
      'Programming Language :: Python :: 3.6',
      'Programming Language :: Python :: 3.7',
      'Programming Language :: Python :: 3.8',
      'Programming Language :: Python :: 3.9'
    ],
    include_package_data=True,
    install_requires=["azure-iot-device"]
)
