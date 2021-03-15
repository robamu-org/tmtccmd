try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from tmtccmd.core.version import SW_VERSION, SW_SUBVERSION

setup(
    name="tmtccmd",
    description="TMTC Commander Core",
    version=f"{SW_VERSION},{SW_SUBVERSION}",
    author="Robin Mueller",
    author_email="robin.mueller.m@gmail.com",
    url="https://github.com/rmspacefish/tmtccmd",
    packages=['tmtccmd'],
    license="Apache-2.0",
    long_description="""\
TMTC Commander Core
Enables satellite software developers to test their on-board software.
Latest:
- Documentation: https://tmtccmd.readthedocs.io/en/latest/
- Project Homepage: https://github.com/rmspacefish/tmtccmd
""",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License:: OSI Approved:: Apache Software License',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Communications',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic:: Scientific / Engineering'
    ],
    platforms='any',
    entry_points={},
    extras_require={},
    install_requires=[
        'crcmod>=1.7',
        'PyQt5>=5.0',
        'pyserial>=3.0'
    ],
)
