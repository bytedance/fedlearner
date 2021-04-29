import os
import platform
from setuptools import setup, find_packages
import time

with open("README.md", "r") as fh:
  long_description = fh.read()

with open('requirements.txt') as f:
    required = f.read().splitlines()

def get_version():
    base = "1.5"
    sysname = platform.system()
    if sysname in ['Darwin']:
        sysname = 'macos'
    else:
        sysname = 'manylinux'

    day = time.strftime('%Y%m%d', time.localtime())
    return '%s.%s.%s'%(base, sysname, day)

setup(
    name='fedlearner',
    version=get_version(),
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
