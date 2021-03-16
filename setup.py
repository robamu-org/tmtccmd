#!/usr/bin/python3
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

# We do the package handling in the setup.py so we can have
setup(
    # package_dir={"": "src"},
    # packages=find_packages(where="src"),
)
