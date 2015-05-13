# Copyright 2013-2015 Michiya Takahashi
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

from azure.storage.blobservice import BlobService
from azure.storage.queueservice import QueueService
from azure.storage.tableservice import TableService

_PY3 = sys.version_info[0] == 3


def _formatName(name, params):
    if _PY3:
        # try all possible formattings
        name = string.Template(name).substitute(**params)
        name = name.format(**params)
    return name % params


class _BlobStorageFileHandler(object):

    def __init__(self,
                  account_name=None,
                  account_key=None,
                  protocol='https',
                  container='logs',
                  zip_compression=False,
                  max_connections=1,
                  max_retries=5,
                  retry_wait=1.0):
        self.service = BlobService(account_name, account_key, protocol)
        self.container_created = False
        hostname = gethostname()
        self.meta = {'hostname': hostname.replace('_', '-'),
                     'process': os.getpid()}
        self.container = (container % self.meta).lower()
        self.meta['hostname'] = hostname
        self.zip_compression = zip_compression
        self.max_connections = max_connections
        self.max_retries = max_retries
        self.retry_wait = retry_wait

    def put_file_into_storage(self, dirName, fileName):
        """
        Ship the outdated log file to the specified blob container.
        """
        if not self.container_created:
            self.service.create_container(self.container)
            self.container_created = True
        fd, tmpfile_path = None, ''
        try:
            file_path = os.path.join(dirName, fileName)
            if self.zip_compression:
                suffix, content_type = '.zip', 'application/zip'
                fd, tmpfile_path = mkstemp(suffix=suffix)
                with os.fdopen(fd, 'wb') as f:
                    with ZipFile(f, 'w', ZIP_DEFLATED) as z:
                        z.write(file_path, arcname=fileName)
                file_path = tmpfile_path
            else:
                suffix, content_type = '', 'text/plain'
            self.service.put_block_blob_from_path(self.container,
                                                  fileName + suffix,
                                                  file_path,
                                                  x_ms_blob_content_type=content_type,
                                                  max_connections=self.max_connections,
                                                  max_retries=self.max_retries,
                                                  retry_wait=self.retry_wait)
        finally:
            if self.zip_compression and fd:
                os.remove(tmpfile_path)


class BlobStorageRotatingFileHandler(RotatingFileHandler,
                                         _BlobStorageFileHandler):
    """
    Handler for logging to a file, which switches from one file
    to the next when the current file reaches a certain size.

    The outdated log file is shipped to the specified Azure Storage
    blob container and removed from the local file system immediately.
    """
    def __init__(self,
                  filename,
                  mode='a',
                  maxBytes=0,
                  encoding=None,
                  delay=False,
                  account_name=None,
                  account_key=None,
                  protocol='https',
                  container='logs',
                  zip_compression=False,
                  max_connections=1,
                  max_retries=5,
                  retry_wait=1.0):
        meta = {'hostname': gethostname(), 'process': os.getpid()}
        RotatingFileHandler.__init__(self,
                                     filename % meta,
                                     mode=mode,
                                     maxBytes=maxBytes,
                                     backupCount=1,
                                     encoding=encoding,
                                     delay=delay)
        _BlobStorageFileHandler.__init__(self,
                                         account_name,
                                         account_key,
                                         protocol,
                                         container,
                                         zip_compression,
                                         max_connections,
                                         max_retries,
                                         retry_wait)

    def doRollover(self):
        """
        Do a rollover, as described in __init__().
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        dfn = "%s.%s" % (self.baseFilename,
                         datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S'))
        if os.path.exists(self.baseFilename):
            os.rename(self.baseFilename, dfn)
            self.put_file_into_storage(*os.path.split(dfn))
            os.remove(dfn)
        if not self.delay:
            self.stream = self._open()


class BlobStorageTimedRotatingFileHandler(TimedRotatingFileHandler,
                                               _BlobStorageFileHandler):
    """
    Handler for logging to a file, rotating the log file at certain timed
    intervals.

    The outdated log file is shipped to the specified Azure Storage
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
                 protocol='https',
                 container='logs',
                 zip_compression=False,
                 max_connections=1,
                 max_retries=5,
                 retry_wait=1.0):
        meta = {'hostname': gethostname(), 'process': os.getpid()}
        TimedRotatingFileHandler.__init__(self,
                                          filename % meta,
                                          when=when,
                                          interval=interval,
                                          backupCount=1,
                                          encoding=encoding,
                                          delay=delay,
                                          utc=utc)
        _BlobStorageFileHandler.__init__(self,
                                         account_name,
                                         account_key,
                                         protocol,
                                         container,
                                         zip_compression,
                                         max_connections,
                                         max_retries,
                                         retry_wait)

    def emit(self, record):
        """
        Emit a record.

        Output the record to the file, catering for rollover as described
        in doRollover().
        """
        record.hostname = self.meta['hostname']
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
                    self.put_file_into_storage(dirName, fileName)
                    result.append(os.path.join(dirName, fileName))
        # delete the stored log file from the local file system immediately
        return result


class QueueStorageHandler(logging.Handler):
    """
    Handler class which sends log messages to a Azure Storage queue.
    """
    def __init__(self, 
                 account_name=None,
                 account_key=None,
                 protocol='https',
                 queue='logs',
                 message_ttl=None,
                 visibility_timeout=None,
                 base64_encoding=False,
                 ):
        """
        Initialize the handler.
        """
        logging.Handler.__init__(self)
        self.service = QueueService(account_name=account_name,
                                    account_key=account_key,
                                    protocol=protocol)
        self.meta = {'hostname': gethostname(), 'process': os.getpid()}
        self.queue = _formatName(queue, self.meta)
        self.queue_created = False
        self.message_ttl = message_ttl
        self.visibility_timeout = visibility_timeout
        self.base64_encoding = base64_encoding

    def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the specified queue.
        """
        try:
            if not self.queue_created:
                self.service.create_queue(self.queue)
                self.queue_created = True
            record.hostname = self.meta['hostname']
            msg = self._encode_text(self.format(record))
            self.service.put_message(self.queue,
                                     msg,
                                     self.visibility_timeout,
                                     self.message_ttl)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def _encode_text(self, text):
        if self.base64_encoding:
            text = b64encode(text.encode('utf-8')).decode('ascii')
        return text


class TableStorageHandler(logging.Handler):
    """
    Handler class which writes log messages to a Azure Storage table.
    """
    MAX_BATCH_SIZE = 100

    def __init__(self, 
                 account_name=None,
                 account_key=None,
                 protocol='https',
                 table='logs',
                 batch_size=0,
                 extra_properties=None,
                 partition_key_formatter=None,
                 row_key_formatter=None,
                 ):
        """
        Initialize the handler.
        """
        logging.Handler.__init__(self)
        self.service = TableService(account_name=account_name,
                                    account_key=account_key,
                                    protocol=protocol)
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
        if batch_size <= 1 or self.service.use_local_storage:
            self.batch = False
        else:
            self.batch = True
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
                self.service.create_table(self.table)
                if self.batch:
                    self.service.begin_batch()
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
            self.service.insert_or_replace_entity(self.table,
                                                  partition_key,
                                                  row_key,
                                                  entity)
            # commit the ongoing batch if it reaches the high mark
            if self.batch:
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
                self.service.commit_batch()
            finally:
                self.rowno = 0
                self.service.begin_batch()

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
