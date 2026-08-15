from os import path
from setuptools import setup
import sys


here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst'), 'rb') as f:
    long_description = f.read().decode('utf-8')

VERSION = '0.11.0'

setup(
    name="pip2nix",
    version=VERSION,
    description='Generate Nix expressions for Python packages.',
    long_description=long_description,
    url="https://github.com/johbo/pip2nix",
    author="Tomasz Kontusz",
    author_email="tomasz.kontusz@gmail.com",
    license='GPLv3+',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],

    keywords='nix pip',

    python_requires='>=3.11',

    install_requires=[
        'configobj==5.0.6',
        'click',
        'jinja2',
        'packaging',
    ],
    packages=['pip2nix', 'pip2nix.models'],
    package_data={'pip2nix': ['*.ini', '*.j2']},
    entry_points={
        "console_scripts": [
            "pip2nix=pip2nix.cli:cli",
            "pip2nix%s=pip2nix.cli:cli" % sys.version[:1],
            "pip2nix%s=pip2nix.cli:cli" % sys.version[:3],
        ],
    }
)
