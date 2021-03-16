try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup


setup(
    package_dir={"": "src"},
    packages=find_packages(where="src"),
)
