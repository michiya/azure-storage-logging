# Copyright 2013-2015 Michiya Takahashi
# Copyright 2022 Abian Rodriguez
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os
import string
import sys
from base64 import b64encode
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from socket import gethostname
from tempfile import mkstemp
from zipfile import ZIP_DEFLATED, ZipFile

from azure.data.tables import TableServiceClient, TableClient

_PY3 = sys.version_info[0] == 3


def _formatName(name, params):
    if _PY3:
        # try all possible formattings
        name = string.Template(name).substitute(**params)
        name = name.format(**params)
    return name % params


class TableStorageHandler(logging.Handler):
    """
    Handler class which writes log messages to a Azure Storage table.
    """
    MAX_BATCH_SIZE = 100
    connection = None
    t_name = None

    def __init__(self, 
                 account_name=None,
                 account_key=None,
                 protocol='https',
                 table='logs',
                 batch_size=0,
                 extra_properties=None,
                 partition_key_formatter=None,
                 row_key_formatter=None,
                 is_emulated=False,
                 conn_str=None
                 ):
        """
        Initialize the handler.
        """
        logging.Handler.__init__(self)
        self.service = TableServiceClient.from_connection_string(conn_str= conn_str)
        self.connection = conn_str
        self.t_name = table
        self.meta = {'hostname': gethostname(), 'process': os.getpid()}
        self.table = _formatName(table, self.meta)
        self.ready = False
        self.rowno = 0
        if not partition_key_formatter:
            # default format for partition keys
            fmt = '%(asctime)s'
            datefmt = '%Y%m%d%H%M'
            partition_key_formatter = logging.Formatter(fmt, datefmt)
        self.partition_key_formatter = partition_key_formatter
        if not row_key_formatter:
            # default format for row keys
            fmt = '%(asctime)s%(msecs)03d-%(hostname)s-%(process)d-%(rowno)02d'
            datefmt = '%Y%m%d%H%M%S'
            row_key_formatter = logging.Formatter(fmt, datefmt)
        self.row_key_formatter = row_key_formatter
        # extra properties and formatters for them
        self.extra_properties = extra_properties
        if extra_properties:
            self.extra_property_formatters = {}
            self.extra_property_names = {}
            for extra in extra_properties:
                if _PY3:
                    f = logging.Formatter(fmt=extra, style=extra[0])
                else:
                    f = logging.Formatter(fmt=extra)
                self.extra_property_formatters[extra] = f
                self.extra_property_names[extra] = self._getFormatName(extra)
        # the storage emulator doesn't support batch operations
        if batch_size <= 1 or is_emulated:
            self.batch = None
        else:
            self.batch = TableBatch()
            if batch_size > TableStorageHandler.MAX_BATCH_SIZE:
                self.batch_size = TableStorageHandler.MAX_BATCH_SIZE
            else:
                self.batch_size = batch_size
        if self.batch:
            self.current_partition_key = None

    def _copyLogRecord(self, record):
        copy = logging.makeLogRecord(record.__dict__)
        copy.exc_info = None
        copy.exc_text = None
        if _PY3:
            copy.stack_info = None
        return copy

    def _getFormatName(self, extra):
        name = extra
        style = extra[0]
        if style == '%':
            name = extra[2:extra.index(')')]
        elif _PY3:
            if style == '{':
                name = next(string.Formatter().parse(extra))[1]
            elif style == '$':
                name = extra[1:]
                if name.startswith('{'):
                    name = name[1:-1]
        return name

    def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the specified table.
        """
        try:
            if not self.ready:
                self.service.create_table_if_not_exists(self.table) #Try to fix the error of table already exists when using just create_table-
                self.ready = True
            # generate partition key for the entity
            record.hostname = self.meta['hostname']
            copy = self._copyLogRecord(record)
            partition_key = self.partition_key_formatter.format(copy)
            # ensure entities in the batch all have the same patition key
            if self.batch:
                if self.current_partition_key is not None:
                    if partition_key != self.current_partition_key:
                        self.flush()
                self.current_partition_key = partition_key
            # add log message and extra properties to the entity
            entity = {}
            if self.extra_properties:
                for extra in self.extra_properties:
                    formatter = self.extra_property_formatters[extra]
                    name = self.extra_property_names[extra]
                    entity[name] = formatter.format(copy)
            entity['message'] = self.format(record)
            # generate row key for the entity
            copy.rowno = self.rowno
            row_key = self.row_key_formatter.format(copy)
            # add entitiy to the table
            entity['PartitionKey'] = partition_key
            entity['RowKey'] = row_key
            # Now it needs a TableClient for this
            t_client = TableClient.from_connection_string(self.connection, self.t_name)
            if not self.batch:
                t_client.create_entity(entity) 
            else:
                #Change to new table client model (This will probably fail, need to improve batches)
                self.batch.insert_or_replace_entity(entity)
                # commit the ongoing batch if it reaches the high mark
                self.rowno += 1
                if self.rowno >= self.batch_size:
                    self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def flush(self):
        """
        Ensure all logging output has been flushed.
        """
        if self.batch and self.rowno > 0:
            try:
                self.service.commit_batch(self.table, self.batch)
            finally:
                self.rowno = 0
                self.batch = TableBatch()

    def setFormatter(self, fmt):
        """
        Set the message formatter.
        """
        super(TableStorageHandler, self).setFormatter(fmt)
        if self.extra_properties:
            logging._acquireLock()
            try:
                for extra in self.extra_property_formatters.values():
                    extra.converter = fmt.converter
                    extra.datefmt = fmt.datefmt
                    if _PY3:
                        extra.default_time_format = fmt.default_time_format
                        extra.default_msec_format = fmt.default_msec_format
            finally:
                logging._releaseLock()

    def setPartitionKeyFormatter(self, fmt):
        """
        Set the partition key formatter.
        """
        self.partition_key_formatter = fmt

    def setRowKeyFormatter(self, fmt):
        """
        Set the row key formatter.
        """
        self.row_key_formatter = fmt
