
import sys
from setuptools import setup
entries = {
    'console_scripts': [
        'pdistcc=pdistcc.cli:main',
        'pdistccd=pdistcc.cli:server_main',
    ]
}
packages = [
    'pdistcc',
    'pdistcc.compiler',
]
install_requires=['uhashring==2.0']

setup(
    name='pdistcc',
    packages=packages,
    entry_points=entries,
    install_requires=install_requires,
)
