#!/usr/bin/env python3
"""
安装脚本
"""

from setuptools import setup, find_packages
import os

# 读取README
with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

# 读取requirements
with open('requirements.txt', 'r', encoding='utf-8') as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith('#')]

setup(
    name='h5-barcode-gun-python',
    version='1.0.0',
    author='h5-barcode-gun',
    description='H5扫码枪 - Python版本',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/your-username/h5-barcode-gun-python',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Office/Business',
        'Topic :: Communications',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Topic :: Multimedia :: Video :: Capture',
        'Topic :: Utilities',
    ],
    keywords='barcode qr-code scanner websocket flask socketio mobile',
    python_requires='>=3.8',
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-asyncio>=0.18.0',
            'black>=21.0.0',
            'flake8>=3.8.0',
            'isort>=5.0.0',
        ],
        'test': [
            'pytest>=6.0',
            'pytest-asyncio>=0.18.0',
            'pytest-cov>=2.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'h5-barcode-server=server:main',
            'h5-barcode-client=pc_client:main',
        ],
    },
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
