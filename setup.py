from setuptools import setup, find_packages


with open("README.md", "r") as fh:
  long_description = fh.read()


setup(
    name='fedlearner',
    version='2.0',
    packages=find_packages(),
    include_package_data=True,
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        'click'
    ],
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: Apache License 2.0",
         "Operating System :: OS Independent",
     ],
)
