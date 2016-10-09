azure-storage-logging
=====================

.. image:: http://img.shields.io/pypi/v/azure-storage-logging.svg?style=flat
    :target: https://pypi.python.org/pypi/azure-storage-logging

.. image:: http://img.shields.io/pypi/l/azure-storage-logging.svg?style=flat
    :target: http://www.apache.org/licenses/LICENSE-2.0.html

*azure-storage-logging* provides functionality to send output from
the standard Python logging APIs to Microsoft Azure Storage.

Dependencies
------------

* azure-storage 0.33 or newer

Installation
------------

Install the package via pip: ::

    pip install azure-storage-logging

Usage
-----

The module **azure_storage_logging.handlers** in the package contains
the following logging handler classes. Each of them uses a different
type of Microsoft Azure Storage to send its output to. They all are subclasses
of the standard Python logging handler classes, so you can make use of them
in the standard ways of Python logging configuration.

In addition to
`the standard formats for logging <http://docs.python.org/2.7/library/logging.html#logrecord-attributes>`_,
the special format ``%(hostname)s`` is also available in your message formatter
for the handlers. The format is introduced for ease of identifying the source
of log messages which come from many computers and go to the same storage.

TableStorageHandler
~~~~~~~~~~~~~~~~~~~
The **TableStorageHandler** class is a subclass of **logging.Handler** class,
and it sends log messages to Azure table storage and store them
as entities in the specified table.

The handler puts a formatted log message from applications in the *message*
property of a table entity along with some system-defined properties
(*PartitionKey*, *RowKey*, and *Timestamp*) like this:

+--------------+-----------+----------------+-------------+
| PartitionKey | RowKey    | Timestamp      | message     |
+==============+===========+================+=============+
| XXXXX        | XXXXXXXXX | YYYY-MM-DD ... | log message |
+--------------+-----------+----------------+-------------+
| XXXXX        | XXXXXXXXX | YYYY-MM-DD ... | log message |
+--------------+-----------+----------------+-------------+
| XXXXX        | XXXXXXXXX | YYYY-MM-DD ... | log message |
+--------------+-----------+----------------+-------------+

* *class* azure_storage_logging.handlers.TableStorageHandler(*account_name=None, account_key=None, protocol='https', table='logs', batch_size=0, extra_properties=None, partition_key_formatter=None, row_key_formatter=None, is_emulated=False*)

    Returns a new instance of the **TableStorageHandler** class. 
    The instance is initialized with the name and the key of your
    Azure Storage account and some optional parameters.

    The *table* specifies the name of the table that stores log messages.
    A new table will be created if it doesn't exist. The table name must
    conform to the naming convention for Azure Storage table, see
    `the naming convention for tables <http://msdn.microsoft.com/library/azure/dd179338.aspx>`_
    for more details.

    The *protocol* specifies the protocol to transfer data between
    Azure Storage and your application, ``http`` and ``https``
    are supported.

    You can specify the *batch_size* in an integer if you want to use
    batch transaction when creating new log entities. If the *batch_size*
    is greater than 1, all new log entities will be transferred to the
    table at a time when the number of new log messages reaches the
    *batch_size*. Otherwise, a new log entity will be transferred to
    the table every time a logging is performed. The *batch_size* must be
    up to 100 (maximum number of entities in a batch transaction for
    Azure Storage table).

    The *extra_properties* accepts a sequence of
    `the formats for logging <http://docs.python.org/2.7/library/logging.html#logrecord-attributes>`_.
    The handler-specific one ``%(hostname)s`` is also acceptable.
    The handler assigns an entity property for every format specified in
    *extra_properties*. Here is an example of using extra properties:

    ::
        
        import logging
        from azure_storage_logging.handlers import TableStorageHandler
        
        # configure the handler and add it to the logger
        logger = logging.getLogger('example')
        handler = TableStorageHandler(account_name='mystorageaccountname',
                                      account_key='mystorageaccountkey',
                                      extra_properties=('%(hostname)s',
                                                        '%(levelname)s'))
        logger.addHandler(handler)
        
        # output log messages
        logger.info('info message')
        logger.warning('warning message')
        logger.error('error message')

    And it will create the log entities, that have the extra properties
    in addition to the regular property *message*, into the table like this:

    +--------------+-----------+----------------+----------+-----------+---------------+
    | PartitionKey | RowKey    | Timestamp      | hostname | levelname | message       |
    +==============+===========+================+==========+===========+===============+
    | XXXXX        | XXXXXXXXX | YYYY-MM-DD ... | myhost   | INFO      | info message  |
    +--------------+-----------+----------------+----------+-----------+---------------+
    | XXXXX        | XXXXXXXXX | YYYY-MM-DD ... | myhost   | WARNING   | warn message  |
    +--------------+-----------+----------------+----------+-----------+---------------+
    | XXXXX        | XXXXXXXXX | YYYY-MM-DD ... | myhost   | ERROR     | error message |
    +--------------+-----------+----------------+----------+-----------+---------------+

    You can specify an instance of your custom **logging.Formatters**
    for the *partition_key_formatter* or the *row_key_formatter*
    if you want to implement your own keys for the table.
    The default formatters will be used for partition keys and row keys
    if no custom formatter for them is given to the handler.
    The default values for partition keys are provided by the format
    ``%(asctime)s`` and the date format ``%Y%m%d%H%M`` (provides a unique
    value per minute). The default values for row keys are provided by the
    format ``%(asctime)s%(msecs)03d-%(hostname)s-%(process)d-%(rowno)02d``
    and the date format ``%Y%m%d%H%M%S``.

    Note that the format ``%(rowno)d`` is a handler-specific one only
    available for row keys. It would be formatted to a sequential and
    unique number in a batch that starts from 0. The format is introduced
    to avoid collision of row keys generated in a batch, and it would
    always be formatted to 0 if you don't use batch transaction for logging
    to the table.

* setPartitionKeyFormatter(*fmt*)

    Sets the handler's formatter for partition keys to *fmt*.

* setRowKeyFormatter(*fmt*)

    Sets the handler's formatter for row keys to *fmt*.

QueueStorageHandler
~~~~~~~~~~~~~~~~~~~

The **QueueStorageHandler** class is a subclass of **logging.Handler** class,
and it pushes log messages to specified Azure storage queue.

You can pop log messages from the queue in other applications
using Azure Storage client libraries.

* *class* azure_storage_logging.handlers.QueueStorageHandler(*account_name=None, account_key=None, protocol='https', queue='logs', message_ttl=None, visibility_timeout=None, base64_encoding=False, is_emulated=False*)

    Returns a new instance of the **QueueStorageHandler** class. 
    The instance is initialized with the name and the key of your
    Azure Storage account and some optional parameters.

    The *queue* specifies the name of the queue that log messages are added.
    A new queue will be created if it doesn't exist. The queue name must
    conform to the naming convention for Azure Storage queue, see
    `the naming convention for queues <http://msdn.microsoft.com/library/azure/dd179349.aspx>`_
    for more details.

    The *protocol* specifies the protocol to transfer data between
    Azure Storage and your application, ``http`` and ``https``
    are supported.

    The *message_ttl* specifies the time-to-live interval for the message,
    in seconds. The maximum time-to-live allowed is 7 days. If this 
    parameter is omitted, the default time-to-live is 7 days.

    The *visibility_timeout* specifies the visibility timeout value,
    in seconds, relative to server time. If not specified, the default
    value is 0 (makes the message visible immediately). The new value
    must be larger than or equal to 0, and cannot be larger than 7 days.
    The *visibility_timeout* cannot be set to a value later than the
    *message_ttl*, and should be set to a value smaller than the
    *message_ttl*. 

    The *base64_encoding* specifies the necessity for encoding
    log text in Base64. If you set this to ``True``, Unicode log text
    in a message is encoded in utf-8 first and then encoded in Base64.
    Some of Azure Storage client libraries or tools assume that
    text messages in Azure Storage queue are encoded in Base64,
    so you can set this to ``True`` to receive log messages correctly
    with those libraries or tools.

BlobStorageRotatingFileHandler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **BlobStorageRotatingFileHandler** class is a subclass of
**logging.handlers.RotatingFileHandler** class. It performs
log file rotation and stores the outdated one in Azure blob storage
container when the current file reaches a certain size.

* *class* azure_storage_logging.handlers.BlobStorageRotatingFileHandler(*filename, mode='a', maxBytes=0, encoding=None, delay=False, account_name=None, account_key=None, protocol='https', container='logs', zip_compression=False, max_connections=1, max_retries=5, retry_wait=1.0*, is_emulated=False)

    Returns a new instance of the **BlobStorageRotatingFileHandler**
    class. The instance is initialized with the name and the key of your
    Azure Storage account and some optional parameters.

    See `RotatingFileHandler <http://docs.python.org/2.7/library/logging.handlers.html#rotatingfilehandler>`_
    for its basic usage. The handler keeps the latest log file into the
    local file system. Meanwhile, the handler sends the outdated log file
    to the blob container immediately and then removes it from the local
    file system.

    The *container* specifies the name of the blob container that stores
    outdated log files. A new container will be created if it doesn't exist.
    The container name must conform to the naming convention for
    Azure Storage blob container, see
    `the naming convention for blob containers <http://msdn.microsoft.com/library/azure/dd135715.aspx>`_
    for more details.

    The *protocol* specifies the protocol to transfer data between
    Azure Storage and your application, ``http`` and ``https``
    are supported.

    The *zip_compression* specifies the necessity for compressing
    every outdated log file in zip format before putting it in
    the container.

    The *max_connections* specifies a maximum number of parallel
    connections to use when the blob size exceeds 64MB.
    Set to 1 to upload the blob chunks sequentially.
    Set to 2 or more to upload the blob chunks in parallel,
    and this uses more system resources but will upload faster.

    The *max_retries* specifies a number of times to retry
    upload of blob chunk if an error occurs.

    The *retry_wait* specifies sleep time in secs between retries.

    The only two formatters ``%(hostname)s`` and ``%(process)d`` are
    acceptable as a part of the *filename* or the *container*. You can save
    log files in a blob container dedicated to each host or process by
    naming containers with these formatters, and also can store log files
    from multiple hosts or processes in a blob container by naming log files
    with them.

    Be careful to use the ``%(process)d`` formatter in the *filename*
    because inconsistent PIDs assigned to your application every time it
    gets started are included as a part of the name of log files to search
    for rotation. You should use the formatter in the *filename* only when
    the log file is generated by a long-running application process.

    Note that the hander class doesn't take the *backupCount* parameter,
    unlike RotatingFileHandler does. The number of outdated log files
    that the handler stores in the container is unlimited, and the files
    are saved with the extension that indicates the time in UTC when
    they are replaced with a new one. If you want to keep the amount of
    outdated log files in the container in a certain number, you will
    need to do that using Azure management portal or other tools.

BlobStorageTimedRotatingFileHandler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **BlobStorageTimedRotatingFileHandler** class is a subclass of
**logging.handlers.TimedRotatingFileHandler** class. It performs
log file rotation and stores the outdated one to Azure blob storage
container at certain timed intervals.

* *class* azure_storage_logging.handlers.BlobStorageTimedRotatingFileHandler(*filename, when='h', interval=1, encoding=None, delay=False, utc=False, account_name=None, account_key=None, protocol='https', container='logs', zip_compression=False, max_connections=1, max_retries=5, retry_wait=1.0*, is_emulated=False)

    Returns a new instance of the **BlobStorageTimedRotatingFileHandler**
    class. The instance is initialized with the name and the key of your
    Azure Storage account and some optional parameters.

    See `TimedRotatingFileHandler <http://docs.python.org/2.7/library/logging.handlers.html#timedrotatingfilehandler>`_
    for its basic usage. The handler keeps the latest log file into the
    local file system. Meanwhile, the handler sends the outdated log file
    to the blob container immediately and then removes it from the local
    file system.

    The *container* specifies the name of the blob container that stores
    outdated log files. A new container will be created if it doesn't exist.
    The container name must conform to the naming convention for
    Azure Storage blob container, see
    `the naming convention for blob containers <http://msdn.microsoft.com/library/azure/dd135715.aspx>`_
    for more details.

    The *protocol* specifies the protocol to transfer data between
    Azure Storage and your application, ``http`` and ``https``
    are supported.

    The *zip_compression* specifies the necessity for compressing
    every outdated log file in zip format before putting it in
    the container.

    The *max_connections* specifies a maximum number of parallel
    connections to use when the blob size exceeds 64MB.
    Set to 1 to upload the blob chunks sequentially.
    Set to 2 or more to upload the blob chunks in parallel,
    and this uses more system resources but will upload faster.

    The *max_retries* specifies a number of times to retry
    upload of blob chunk if an error occurs.

    The *retry_wait* specifies sleep time in secs between retries.

    The only two formatters ``%(hostname)s`` and ``%(process)d`` are
    acceptable as a part of the *filename* or the *container*. You can save
    log files in a blob container dedicated to each host or process by
    naming containers with these formatters, and also can store log files
    from multiple hosts or processes in a blob container by naming log files
    with them.

    Be careful to use the ``%(process)d`` formatter in the *filename*
    because inconsistent PIDs assigned to your application every time it
    gets started are included as a part of the name of log files to search
    for rotation. You should use the formatter in the *filename* only when
    the log file is generated by a long-running application process.

    Note that the hander class doesn't take the *backupCount* parameter,
    unlike TimedRotatingFileHandler does. The number of outdated log files
    that the handler stores in the container is unlimited.
    If you want to keep the amount of outdated log files in the container
    in a certain number, you will need to do that using Azure
    management portal or other tools.

Example
-------

Here is an example of the configurations and the logging that uses
three different types of storage from the logger:

::

    LOGGING = {
        'version': 1,
        'formatters': {
            'simple': {
                'format': '%(asctime)s %(message)s',
            },
            'verbose': {
                'format': '%(asctime)s %(levelname)s %(hostname)s %(process)d %(message)s',
            },
            # this is the same as the default, so you can skip configuring it
            'partition_key': {
                'format': '%(asctime)s',
                'datefmt': '%Y%m%d%H%M',
            },
            # this is the same as the default, so you can skip configuring it
            'row_key': {
                'format': '%(asctime)s%(msecs)03d-%(hostname)s-%(process)d-%(rowno)02d',
                'datefmt': '%Y%m%d%H%M%S',
            },
        },
        'handlers': {
            'file': {
                'account_name': 'mystorageaccountname',
                'account_key': 'mystorageaccountkey',
                'protocol': 'https',
                'level': 'DEBUG',
                'class': 'azure_storage_logging.handlers.BlobStorageTimedRotatingFileHandler',
                'formatter': 'verbose',
                'filename': 'example.log',
                'when': 'D',
                'interval': 1,
                'container': 'logs-%(hostname)s',
                'zip_compression': False,
            },
            'queue': {
                'account_name': 'mystorageaccountname',
                'account_key': 'mystorageaccountkey',
                'protocol': 'https',
                'queue': 'logs',
                'level': 'CRITICAL',
                'class': 'azure_storage_logging.handlers.QueueStorageHandler',
                'formatter': 'verbose',
            },
            'table': {
                'account_name': 'mystorageaccountname',
                'account_key': 'mystorageaccountkey',
                'protocol': 'https',
                'table': 'logs',
                'level': 'INFO',
                'class': 'azure_storage_logging.handlers.TableStorageHandler',
                'formatter': 'simple',
                'batch_size': 20,
                'extra_properties': ['%(hostname)s', '%(levelname)s'],
                'partition_key_formatter': 'cfg://formatters.partition_key',
                'row_key_formatter': 'cfg://formatters.row_key',
            },
        },
        'loggers': {
            'example': {
                'handlers': ['file', 'queue', 'table'],
                'level': 'DEBUG',
            },
        }
    }
    
    import logging
    from logging.config import dictConfig

    dictConfig(LOGGING)
    logger = logging.getLogger('example')
    logger.debug('debug message')
    logger.info('info message')
    logger.warning('warning message')
    logger.error('error message')
    logger.critical('critical message') 

Notice
------

* Set *is_emulated* to ``True`` at initialization of the logging handlers
  if you want to use this package with Azure storage emulator.

License
-------

Apache License 2.0

Credits
-------

-  `Michiya Takahashi <http://github.com/michiya/>`__
