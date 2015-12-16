from distutils.core import setup
from setuptools import find_packages

setup(
    name='wolverine',
    version='0.3.0',
    packages=find_packages(),
    url='http://github.com/drankinn/wolverine',
    license='MIT 2.0',
    author='Lance Andersen',
    author_email='techlance@gmail.com',
    description='micro service framework with python 3.5 and asyncio',
    package_data={'': ['*.ini']},
    install_requires=[
        'aiohttp>=0.17.4',
        'aiozmq>=0.7.1',
        'msgpack-python>=0.4.6',
        'python-consul>=0.4.5',
        'pyzmq>=14.4.1'
    ]
)
