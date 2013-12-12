# Copyright 2013 Michiya Takahashi
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
import os
from logging import Formatter, Handler
from logging.handlers import TimedRotatingFileHandler
from socket import gethostname

from azure.storage.blobservice import BlobService
from azure.storage.queueservice import QueueService
from azure.storage.tableservice import TableService


class BlobStorageTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Handler for logging to a file, rotating the log file at certain timed
    intervals.

    The outdated log file is shipped to the specified Windows Azure Storage
    blob container and removed from the local file system immediately.
    """

    def __init__(self,
                 filename,
                 when='h',
                 interval=1,
                 encoding=None,
                 delay=False,
                 utc=False,
                 account_name=None,
                 account_key=None,
                 protocol='http',
                 container='logs',
                 ):
        hostname = gethostname()
        meta = {'hostname': hostname, 'process': os.getpid()}
        s = super(BlobStorageTimedRotatingFileHandler, self)
        s.__init__(filename % meta,
                   when=when,
                   interval=interval,
                   backupCount=1,
                   encoding=encoding,
                   delay=delay,
                   utc=utc)
        self.service = BlobService(account_name, account_key, protocol)
        self.container_created = False
        meta['hostname'] = hostname.replace('_', '-')
        container = container % meta
        self.container = container.lower()
        self.hostname = hostname

    def _put_log(self, dirName, fileName):
        """
        Ship the outdated log file to the specified blob container.
        """
        if not self.container_created:
            self.service.create_container(self.container)
            self.container_created = True
        self.service.put_blob(self.container,
                              fileName,
                              file(os.path.join(dirName, fileName)).read(),
                              'BlockBlob',
                              x_ms_blob_content_type='text/plain',
                              )

    def emit(self, record):
        """
        Emit a record.

        Output the record to the file, catering for rollover as described
        in doRollover().
        """
        record.hostname = self.hostname
        super(BlobStorageTimedRotatingFileHandler, self).emit(record)

    def getFilesToDelete(self):
        """
        Determine the files to delete when rolling over.
        """
        dirName, baseName = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        result = []
        prefix = baseName + "."
        plen = len(prefix)
        for fileName in fileNames:
            if fileName[:plen] == prefix:
                suffix = fileName[plen:]
                if self.extMatch.match(suffix):
                    self._put_log(dirName, fileName)
                    result.append(os.path.join(dirName, fileName))
        # delete the stored log file from the local file system immediately
        return result


class QueueStorageHandler(Handler):
    """
    Handler class which sends log messages to a Windows Azure Storage queue.
    """

    def __init__(self, 
                 account_name=None,
                 account_key=None,
                 protocol='http',
                 queue='logs',
                 message_ttl=None,
                 visibility_timeout=None,
                 ):
        """
        Initialize the handler.
        """
        Handler.__init__(self)
        self.service = QueueService(account_name=account_name,
                                    account_key=account_key,
                                    protocol=protocol)
        hostname = gethostname()
        meta = {'hostname': hostname, 'process': os.getpid()}
        self.queue = queue % meta
        self.queue_created = False
        self.hostname = hostname
        self.message_ttl = message_ttl
        self.visibility_timeout = visibility_timeout

    def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the specified queue.
        """
        try:
            if not self.queue_created:
                self.service.create_queue(self.queue)
                self.queue_created = True
            record.hostname = self.hostname
            msg = self.format(record)
            self.service.put_message(self.queue,
                                     msg,
                                     self.visibility_timeout,
                                     self.message_ttl)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class TableStorageHandler(Handler):
    """
    Handler class which writes log messages to a Windows Azure Storage table.
    """
    _MAX_BATCH_SIZE=100

    def __init__(self, 
                 account_name=None,
                 account_key=None,
                 protocol='http',
                 table='logs',
                 batch_size=0,
                 extra_properties=None,
                 partition_key_formatter=None,
                 row_key_formatter=None,
                 ):
        """
        Initialize the handler.
        """
        Handler.__init__(self)
        self.service = TableService(account_name=account_name,
                                    account_key=account_key,
                                    protocol=protocol)
        hostname = gethostname()
        meta = {'hostname': hostname, 'process': os.getpid()}
        self.table = table % meta
        self.table_created = False
        self.hostname = hostname
        self.rowno = 0
        self.extra_properties = []
        if extra_properties:
            self.extra_properties.extend(extra_properties)
        self.default_formatter = Formatter()
        if not partition_key_formatter:
            # use default format for partition key
            fmt = '%(asctime)s'
            datefmt = '%Y%m%d%H%M'
            partition_key_formatter = Formatter(fmt, datefmt)
        self.partition_key_formatter = partition_key_formatter
        if not row_key_formatter:
            # use default format for row key
            fmt = '%(asctime)s%(msecs)03d-%(hostname)s-%(process)d-%(rowno)02d'
            datefmt = '%Y%m%d%H%M%S'
            row_key_formatter = Formatter(fmt, datefmt)
        self.row_key_formatter = row_key_formatter
        # the storage emulator doesn't support batch operations
        if batch_size <= 1 or self.service.use_local_storage:
            self.batch = False
        else:
            self.batch = True
            if batch_size > TableStorageHandler._MAX_BATCH_SIZE:
                self.batch_size = TableStorageHandler._MAX_BATCH_SIZE
            else:
                self.batch_size = batch_size
        if self.batch:
            self.current_partition_key = None

    def _getFormatter(self):
        """
        Get the formatter for internal use.
        """
        if self.formatter:
            fmt = self.formatter
            formatter = Formatter(fmt=fmt._fmt, datefmt=fmt.datefmt)
            formatter.converter = fmt.converter
        else:
            formatter = self.default_formatter
        return formatter

    def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the specified table.
        """
        try:
            if not self.table_created:
                self.service.create_table(self.table)
                self.table_created = True
                if self.batch:
                    self.service.begin_batch()
            # generate partition key for the entity
            record.hostname = self.hostname
            partition_key = self.partition_key_formatter.format(record)
            # ensure entities in the batch all have the same patition key
            if self.batch:
                if self.current_partition_key is not None:
                    if partition_key != self.current_partition_key:
                        self.flush()
                        self.service.begin_batch()
                self.current_partition_key = partition_key
            # add log message and extra properties to the entity
            entity = {}
            if self.extra_properties:
                fmt = self._getFormatter()
                for extra in self.extra_properties:
                    idx = extra.find(')')
                    if extra.startswith('%(') and idx != -1:
                        fmt._fmt = extra
                        prop_name = extra[2:idx]
                        value = fmt.format(record)
                        entity[prop_name] = value
            entity['message'] = self.format(record)
            # generate row key for the entity
            record.rowno = self.rowno
            row_key = self.row_key_formatter.format(record)
            del record.rowno
            # add entitiy to the table
            self.service.insert_or_replace_entity(self.table,
                                                  partition_key,
                                                  row_key,
                                                  entity)
            # commit the ongoing batch if it reaches the high mark
            if self.batch:
                self.rowno += 1
                if self.rowno >= self.batch_size:
                    self.flush()
                    self.service.begin_batch()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def flush(self):
        """
        Ensure all logging output has been flushed.
        """
        if self.batch:
            self.service.commit_batch()
            self.rowno = 0

    def setPartitionKeyFormatter(self, fmt):
        """
        Set the formatter for the partition key.
        """
        self.partition_key_formatter = fmt

    def setRowKeyFormatter(self, fmt):
        """
        Set the formatter for the row key.
        """
        self.row_key_formatter = fmt
