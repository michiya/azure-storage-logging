azure-storage-logging_updated
=================================

.. image:: http://img.shields.io/pypi/v/azure-storage-logging.svg?style=flat
    :target: https://pypi.python.org/pypi/azure-storage-logging

.. image:: http://img.shields.io/pypi/l/azure-storage-logging.svg?style=flat
    :target: http://www.apache.org/licenses/LICENSE-2.0.html

*azure-storage-logging_table* is a fork from *azure-storage-logging* out of the author's necesity to send output from the standard Python logging APIs to Microsoft Azure Storage Tables.
Due to the original module by Michiya Takahashi being outdated, it modifies it to restore functionality to the TableStorageHandler for logging. 
In the future, more functionalities may be restored. But on this current version only the TableStorageHandler is usable.

Dependencies
------------

* azure-data-tables 12.4.0

Installation
------------

Install the package via pip: ::

    pip install azure-storage-logging_table

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
        handler = TableStorageHandler(conn_str='myConnectionString', table='myTableName',
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
            'table': {
                'conn_str': DefaultEndpointsProtocol=https;AccountName=test;AccountKey=akey==;EndpointSuffix=core.windows.net'
                'protocol': 'https',
                'table': 'logs',
                'level': 'INFO',
                'class': 'azure_storage_logging.handlers.TableStorageHandler',
                'formatter': 'simple',
                'extra_properties': ['%(hostname)s', '%(levelname)s'],
                'partition_key_formatter': 'cfg://formatters.partition_key',
                'row_key_formatter': 'cfg://formatters.row_key',
            },
        },
        'loggers': {
            'example': {
                'handlers': ['table'],
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

-  `Abian Rodriguez <http://github.com/AbianG>`__
-  `Michiya Takahashi <http://github.com/michiya/>`__