from distutils.core import setup
from setuptools import find_packages

setup(
    name='wolverine',
    version='0.3.1',
    packages=find_packages(),
    url='http://github.com/drankinn/wolverine',
    license='MIT 2.0',
    author='Lance Andersen',
    author_email='techlance@gmail.com',
    description='micro service framework with python 3.5 and asyncio',
    package_data={'': ['*.ini']},
    install_requires=[
        'aiohttp>=0.19.0',
        'aiozmq>=0.7.1',
        'msgpack-python>=0.4.6',
        'python-consul>=0.4.7',
        'pyzmq>=15.1.0'
    ]
)
