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
    'Topic :: System :: Logging',
]

setup(
    name='azure-storage-logging',
    version='0.2.1',
    description='Logging handlers to send logging output to Microsoft Azure Storage',
    long_description=open('README.rst').read(),
    author='Michiya Takahashi',
    author_email='michiya.takahashi@gmail.com',
    url='https://github.com/michiya/azure-storage-logging',
    license='Apache License 2.0',
    packages=['azure_storage_logging'],
    install_requires=[
        'azure',
    ],
    classifiers=CLASSIFIERS,
    keywords='azure logging',
)
