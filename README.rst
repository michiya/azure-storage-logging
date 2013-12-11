azure-storage-logging
=====================

*azure-storage-logging* provides functionality to send output from
the standard Python logging APIs to Windows Azure Storage.

Dependencies
------------

* azure

Installation
------------

Install the package via pip: ::

    pip install azure-storage-logging

Usage
-----

The module **azure_storage_logging.handlers** in the package contains
the following logging handler classes. Each of them uses a different
type of Windows Azure Storage to send its output to. They all are subclasses
of the standard Python logging handler classes, so you can make use of them
in the standard ways of Python logging configuration.

In addition to the standard Python formats for logging, the special format
``%(hostname)s`` is available in the message formatter for the handlers.
The format is introduced for ease of identifying the source of log messages
when logs from many computers are gathered into one location.

TableStorageHandler
~~~~~~~~~~~~~~~~~~~
The **TableStorageHandler** class is a subclass of **logging.Handler** class,
and it sends log messages to Windows Azure table storage and store them
as entities in the specified table.

The handler puts a formatted log message from applications in the *message*
property of a table entity along with some system-defined properties
(*PartitionKey*, *RowKey*, and *Timestamp*) like this:

+--------------+-----------+----------------+-------------+
| PartitionKey | RowKey    | Timestamp      | message     |
+==============+===========+================+=============+
| XXXXX        | XXXXXXXXX | yyyy/mm/dd ... | log message |
+--------------+-----------+----------------+-------------+
| XXXXX        | XXXXXXXXX | yyyy/mm/dd ... | log message |
+--------------+-----------+----------------+-------------+
| XXXXX        | XXXXXXXXX | yyyy/mm/dd ... | log message |
+--------------+-----------+----------------+-------------+

* *class* azure_storage_logging.handlers.TableStorageHandler(*account_name=None, account_key=None, protocol='http', table='logs', batch=False, batch_size=100, extra_properties=None, partition_key_formatter=None, row_key_formatter=None*)

    Returns a new instance of the **TableStorageHandler** class. 
    The instance is initialized with the name and the key of your
    Windows Azure Storage account and some optional parameters.

    The *table* specifies the name of the table that stores log messages.
    The table name must conform to the naming convention for Windows Azure
    Storage table, see
    `the naming convention for tables <http://msdn.microsoft.com/en-us/library/windowsazure/dd179338.aspx>`_
    for more details. A new table will be created if it doesn't exist.

    The *protocol* specifies the protocol to transfer data between
    Windows Azure Storage and your application, ``http`` and ``https``
    are supported.

    You can specify the *batch* and the *batch_size* if you want to use
    batch transaction when creating new log entities. If the *batch* is
    ``True``, all new log entities will be transferred to the table
    at a time when the number of log messages reaches the *batch_size*.
    Otherwise, a new log entity will be transferred to the table
    every time a logging is performed. The *batch_size* is set to 100
    (maximum number of entities in a batch transaction for Windows Azure
    Storage table) by default, and is ignored when the *batch* is ``False``.

    The *extra_properties* accepts a sequence of bare formatters for
    **logging.LogRecord** listed
    `here <http://docs.python.org/2.7/library/logging.html#logrecord-attributes>`_.
    The handler-specific formatter ``%(hostname)s`` is also acceptable.
    The handler assigns an entity property for every formatter specified in
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
        logger.warn('warn message')
        logger.error('error message')

    And it will create the log entities, that have the extra properties
    in addition to the regular property *message*, to the table like this:

    +--------------+-----------+----------------+----------+-----------+---------------+
    | PartitionKey | RowKey    | Timestamp      | hostname | levelname | message       |
    +==============+===========+================+==========+===========+===============+
    | XXXXX        | XXXXXXXXX | yyyy/mm/dd ... | myhost   | INFO      | info message  |
    +--------------+-----------+----------------+----------+-----------+---------------+
    | XXXXX        | XXXXXXXXX | yyyy/mm/dd ... | myhost   | WARNING   | warn message  |
    +--------------+-----------+----------------+----------+-----------+---------------+
    | XXXXX        | XXXXXXXXX | yyyy/mm/dd ... | myhost   | ERROR     | error message |
    +--------------+-----------+----------------+----------+-----------+---------------+

    You can specify an instance of your custom **logging.Formatters**
    for the *partition_key_formatter* or the *row_key_formatter*
    if you want to implement your own partition keys or row keys for
    the table. The default formatters will be applied for partition keys
    and row keys if no custom formatter for them is given to the handler.
    The default values for partition keys are provided by the format
    ``%(asctime)s`` and the date format ``%Y%m%d%H%M`` (provides a unique
    value per minute). The default values for row keys are provided by the
    format ``%(asctime)s%(msecs)03d-%(hostname)s-%(process)d-%(rowno)02d``
    and the date format ``%Y%m%d%H%M%S``. Note that the format
    ``%(rowno)d`` is a handler-specific one only available for row keys.
    It would be formatted to sequential number that starts from 0,
    and a unique number in a batch. The format is introduced to avoid
    collision of row keys generated in a batch, and it would always be
    formatted to 0 if the *batch* is ``False``.

* setPartitionKeyFormatter(*fmt*)

    Sets the handler's formatter for partition keys to *fmt*.

* setRowKeyFormatter(*fmt*)

    Sets the handler's formatter for row keys to *fmt*.

QueueStorageHandler
~~~~~~~~~~~~~~~~~~~

The **QueueStorageHandler** class is a subclass of **logging.Handler** class,
and it sends log messages to Windows Azure queue storage and enqueue them
to the specified queue.

* *class* azure_storage_logging.handlers.QueueStorageHandler(*account_name=None, account_key=None, protocol='http', queue='logs', message_ttl=None, visibility_timeout=None*)

    Returns a new instance of the **QueueStorageHandler** class. 
    The instance is initialized with the name and the key of your
    Windows Azure Storage account and some optional parameters.

    The *queue* specifies the name of the queue that log messages are
    added. The queue name must conform to the naming convention for
    Windows Azure Storage queue, see
    `the naming convention for queues <http://msdn.microsoft.com/en-us/library/windowsazure/dd179349.aspx>`_
    for more details. A new queue will be created if it doesn't exist.

    The *protocol* specifies the protocol to transfer data between
    Windows Azure Storage and your application, ``http`` and ``https``
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

    You can receive log messages in the queue on other applications,
    not necessarily written in Python, using Windows Azure Storage client
    library.

BlobStorageTimedRotatingFileHandler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **BlobStorageTimedRotatingFileHandler** class is a subclass of
**logging.handlers.TimedRotatingFileHandler** class, and it does the rotation
of log files and storing the outdated log files to the specified container of
Windows Azure blob storage at certain timed intervals.

* *class* azure_storage_logging.handlers.BlobStorageTimedRotatingFileHandler(*filename, when='h', interval=1, encoding=None, delay=False, utc=False, account_name=None, account_key=None, protocol='http', container='logs'*)

    Returns a new instance of the **BlobStorageTimedRotatingFileHandler**
    class. The instance is initialized with the name and the key of your
    Windows Azure Storage account and some optional parameters.

    See `TimedRotatingFileHandler <http://docs.python.org/2.7/library/logging.handlers.html#timedrotatingfilehandler>`_
    for its basic usage. The handler keeps the latest log file into the
    local file system. Meanwhile, the handler sends the outdated log file
    to the blob container immediately and then removes it from the local
    file system.

    The *container* specifies the name of the blob container that stores
    outdated log files. The container name must conform to the naming
    convention for Windows Azure Storage blob container, see
    `the naming convention for blob containers <http://msdn.microsoft.com/en-us/library/windowsazure/dd135715.aspx>`_
    for more details. A new container will be created if it doesn't exist.

    The *protocol* specifies the protocol to transfer data between
    Windows Azure Storage and your application, ``http`` and ``https``
    are supported.

    The only two formatters ``%(hostname)s`` and ``%(process)d`` are
    acceptable as a part of the *filename* or the *container*. You can save
    log files in a blob container dedicated to each host or process by
    naming containers with these formatters, and also can store log files
    from multiple hosts or processes in a blob container by naming log files
    with them.

    Be careful when you use the ``%(process)d`` formatter in the *filename*
    because inconsistent PIDs assigned to your application every time it
    gets started are included as a part of the name of log files to search
    for rotation. You should use the formatter in the *filename* only when
    the log file is generated by a long-running application process.

    Note that the hander class doesn't take the *backupCount* parameter.
    The outdated log files stored in the blob container by the handler
    are unlimited in number. If you want to keep the amount of outdated
    log files in the blob container in a certain number, you will need to
    do this using Windows Azure management portal or some other tools.

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
                'batch': True,
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
    logger.warn('warn message')
    logger.error('error message')
    logger.critical('critical message') 

Notice
------

* Follow the instructions below if you want to use this package with
  Windows Azure storage emulator that is bundled with Windows Azure SDK:

    * If your application is not going to run on Windows Azure compute
      emulator, set ``EMULATED`` environment variable as ``True`` at first.

    * specify nothing for the *account_name* and the *account_key*,
      and specify ``http`` for the *protocol* at initialization of
      the logging handlers.

License
-------

Apache License 2.0

Credits
-------

-  `Michiya Takahashi <http://github.com/michiya/>`__
