try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from tmtccmd.core.version import SW_VERSION, SW_SUBVERSION

setup(
    version=f"{SW_VERSION},{SW_SUBVERSION}",
    install_requires=[
        'crcmod>=1.7',
        'PyQt5>=5.0',
        'pyserial>=3.0'
    ],
)
