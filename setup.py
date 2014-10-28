#!/usr/bin/env python
from setuptools import find_packages, setup
__version__="0.1.0"
from os import path
import os, commands

with open('tools/pip-requires', 'r') as f:
    requires = [x.strip() for x in f if x.strip()]

def get_files(dir_path):
    if not dir_path.endswith('/'):
        dir_path = dir_path + '/'
    return [dir_path+f_name for f_name in os.listdir(dir_path) if f_name!='.svn']

scripts = get_files('bin')
services = get_files('etc/init.d')

install_services = []
for i, service in enumerate(services):
    if not os.path.basename(service) in os.listdir('/etc/init.d'):
        commands.getstatusoutput('chmod +x ' + service)
        install_services.append(service)

setup(
    name='chimera',
    version=__version__,
    description='chimera',
    author='JDOS',
    author_email='JDOS@mail.com',
    url='http://JDOS.com',
    packages=find_packages(exclude=['tests', 'benchmarks']),
    install_requires=requires,
    zip_safe=False,
    long_description=open(
        path.join(
            path.dirname(__file__),
            'README'
        )
    ).read(),
    test_suite='nose.collector',
    classifiers=[
        "Programming Language :: Python",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Internet",
        "Topic :: Software Development :: System :: Python Systems",
        "Intended Audience :: Developers",
        "Development Status :: 1 - Beta",
    ],

    scripts=scripts,
    data_files=[('/etc/init.d/', install_services)],
    
    entry_points={
        'chimera.api.v1':[
            'networks=chimera.api.v1.networks:blueprint',
            ],
        'chimera.api.v1.extensions':[
            'diagnostics = chimera.api.v1.extensions.diagnostics:blueprint',
            ],
        }
)
