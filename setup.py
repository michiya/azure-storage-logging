try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

CLASSIFIERS=[
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: Apache Software License',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Topic :: System :: Logging',
]

setup(
    name='azure-storage-logging_updated',
    version='0.6.0',
    description='Logging handlers to send logs to Microsoft Azure Storage',
    long_description=open('README.rst').read(),
    author='Abian Rodriguez',
    author_email='abiangrodriguez@protonmail.com',
    url='https://github.com/AbianG/azure-storage-logging_updated',
    license='Apache License 2.0',
    packages=['azure_storage_logging'],
    install_requires=[
        'azure-data-tables==12.2.0'
    ],
    classifiers=CLASSIFIERS,
    keywords='azure logging',
)
