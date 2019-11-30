import setuptools
import sys

sys.path.insert(0, 'src')
from iotc import __version__, __name__

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name=__name__,
    version=__version__,
    author="Oguz Bastemur",
    author_email="ogbastem@microsoft.com",
    description="Azure IoT Central device client for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Azure/iot-central-firmware",
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
      'Programming Language :: Python :: 3.6',
      'Programming Language :: Python :: Implementation :: CPython',
      'Programming Language :: Python :: Implementation :: PyPy'
    ],
    include_package_data=True,
    install_requires=["paho-mqtt", "httplib2"]
)
