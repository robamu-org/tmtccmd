try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup


setup(
    packages=["tmtccmd.core", ],
)
