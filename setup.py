import os
import subprocess
from setuptools import setup, find_packages
import time

with open("README.md", "r") as fh:
  long_description = fh.read()

with open('requirements.txt') as f:
    required = f.read().splitlines()

_VERSION = '1.5.0.dev%s'%(time.strftime('%Y%m%d', time.localtime()))
setup(
    name='fedlearner',
    version=_VERSION.replace('-', ''),
    packages=find_packages(),
    include_package_data=True,
    author='Fedlearner Contributors',
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=required,
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: Apache Software License",
         "Operating System :: MacOS",
         "Operating System :: POSIX :: Linux"
     ],
)
