try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    version='1.0',
    packages=['core','com_if','defaults','pus_tc','pus_tm','sendreceive','utility'],
)
