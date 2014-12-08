# -*- coding: utf-8 -*-
import logging
import os
import sys
import time
import unittest

from base64 import b64encode
from datetime import datetime
from logging.config import dictConfig
from shutil import rmtree
from socket import gethostname
from threading import current_thread
from tempfile import mkdtemp

from azure.storage import BlobService, QueueService, TableService


# put your Azure Storage account name and key here
ACCOUNT_NAME = ''
ACCOUNT_KEY = ''

# uncomment the next line if you run the test on Azure Storage emulator
#os.environ.update({'EMULATED': 'True'})


_PY3 = sys.version_info[0] == 3

_LOGFILE_TMPDIR = mkdtemp()

_EMULATED =  'EMULATED' in os.environ and os.environ['EMULATED'].lower() != 'false'
if _EMULATED:
    ACCOUNT_NAME = None
    ACCOUNT_KEY = None

LOGGING = {
    'version': 1,
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(message)s',
        },
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(hostname)s %(process)d %(message)s',
        },
        'batch_test_partition_key': {
            # fixate partition keys to avoid unexpected batch commit during the test
            'format': 'batch-%(hostname)s',
        },
        'custom_partition_key': {
            'format': 'mycustompartitionkey-%(hostname)s-%(asctime)s',
            'datefmt': '%Y%m%d',
        },
        'custom_row_key': {
            'format': 'mycustomrowkey-%(hostname)s-%(asctime)s',
            'datefmt': '%Y%m%d%H%M',
        },
    },
    'handlers': {
        # BlobStorageTimedFileRotatingHandlerTest
        'file': {
            'account_name': ACCOUNT_NAME,
            'account_key': ACCOUNT_KEY,
            'protocol': 'https',
            'level': 'DEBUG',
            'class': 'azure_storage_logging.handlers.BlobStorageTimedRotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(_LOGFILE_TMPDIR, 'test.log'),
            'when': 'S',
            'interval': 10,
            'container': 'logs-%s' % gethostname(),
        },
        # QueueStorageHandlerTest
        'queue': {
            'account_name': ACCOUNT_NAME,
            'account_key': ACCOUNT_KEY,
            'protocol': 'https',
            'queue': 'queue-storage-handler-test',
            'level': 'INFO',
            'class': 'azure_storage_logging.handlers.QueueStorageHandler',
            'formatter': 'simple',
        },
        'message_ttl': {
            'account_name': ACCOUNT_NAME,
            'account_key': ACCOUNT_KEY,
            'protocol': 'https',
            'queue': 'queue-storage-handler-test',
            'level': 'INFO',
            'class': 'azure_storage_logging.handlers.QueueStorageHandler',
            'formatter': 'simple',
            'message_ttl': 10,
        },
        'visibility_timeout': {
            'account_name': ACCOUNT_NAME,
            'account_key': ACCOUNT_KEY,
            'protocol': 'https',
            'queue': 'queue-storage-handler-test',
            'level': 'INFO',
            'class': 'azure_storage_logging.handlers.QueueStorageHandler',
            'formatter': 'simple',
            'visibility_timeout': 10,
        },
        'base64_encoding': {
            'account_name': ACCOUNT_NAME,
            'account_key': ACCOUNT_KEY,
            'protocol': 'https',
            'queue': 'queue-storage-handler-test',
            'level': 'INFO',
            'class': 'azure_storage_logging.handlers.QueueStorageHandler',
            'formatter': 'simple',
            'base64_encoding': True,
        },
        # TableStorageHandlerTest
        'table': {
            'account_name': ACCOUNT_NAME,
            'account_key': ACCOUNT_KEY,
            'protocol': 'https',
            'table': 'TableStorageHandlerTest',
            'level': 'INFO',
            'class': 'azure_storage_logging.handlers.TableStorageHandler',
            'formatter': 'simple',
        },
        'batch': {
            'account_name': ACCOUNT_NAME,
            'account_key': ACCOUNT_KEY,
            'protocol': 'https',
            'table': 'TableStorageHandlerTest',
            'level': 'INFO',
            'class': 'azure_storage_logging.handlers.TableStorageHandler',
            'formatter': 'simple',
            'batch_size': 10,
            'partition_key_formatter': 'cfg://formatters.batch_test_partition_key',
        },
        'extra_properties': {
            'account_name': ACCOUNT_NAME,
            'account_key': ACCOUNT_KEY,
            'protocol': 'https',
            'table': 'TableStorageHandlerTest',
            'level': 'INFO',
            'class': 'azure_storage_logging.handlers.TableStorageHandler',
            'formatter': 'simple',
            'extra_properties': [
                '%(hostname)s',
                '%(levelname)s',
                '%(levelno)s',
                '%(module)s',
                '%(name)s',
                '%(process)d',
                '%(thread)d',
            ],
        },
        'custom_keys': {
            'account_name': ACCOUNT_NAME,
            'account_key': ACCOUNT_KEY,
            'protocol': 'https',
            'table': 'TableStorageHandlerTest',
            'level': 'INFO',
            'class': 'azure_storage_logging.handlers.TableStorageHandler',
            'formatter': 'simple',
            'partition_key_formatter': 'cfg://formatters.custom_partition_key',
            'row_key_formatter': 'cfg://formatters.custom_row_key',
        },
    },
    'loggers': {
        # BlobStorageTimedFileRotatingHandlerTest
        'file': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
        # QueueStorageHandlerTest
        'queue': {
            'handlers': ['queue'],
            'level': 'DEBUG',
        },
        'message_ttl': {
            'handlers': ['message_ttl'],
            'level': 'DEBUG',
        },
        'visibility_timeout': {
            'handlers': ['visibility_timeout'],
            'level': 'DEBUG',
        },
        'base64_encoding': {
            'handlers': ['base64_encoding'],
            'level': 'DEBUG',
        },
        # TableStorageHandlerTest
        'table': {
            'handlers': ['table'],
            'level': 'DEBUG',
        },
        'batch': {
            'handlers': ['batch'],
            'level': 'DEBUG',
        },
        'extra_properties': {
            'handlers': ['extra_properties'],
            'level': 'DEBUG',
        },
        'custom_keys': {
            'handlers': ['custom_keys'],
            'level': 'DEBUG',
        },
    }
}

def _base64_encode(text):
    return b64encode(text.encode('utf-8')).decode('ascii')

def _get_formatter_config_value(formatter_name, key):
    return _get_logging_config_value('formatters', formatter_name, key)

def _get_handler_config_value(handler_name, key):
    return _get_logging_config_value('handlers', handler_name, key)

def _get_handler_name(logger_name):
    return next(iter(_get_logger_config_value(logger_name, 'handlers')))

def _get_logger_config_value(logger_name, key):
    return _get_logging_config_value('loggers', logger_name, key)

def _get_logging_config_value(kind, name, key):
    try:
        value = LOGGING[kind][name][key]
    except KeyError:
        value = None
    return value


class _TestCase(unittest.TestCase):

    if not _PY3:
        def assertRegex(self, text, regex, msg=None):
            return self.assertRegexpMatches(text, regex, msg)


class BlobStorageTimedRotatingFileHandlerTest(_TestCase):
    
    def _get_container_name(self, handler_name):
        container = _get_handler_config_value(handler_name, 'container')
        if container:
            container = container.replace('_', '-').lower()
        return container

    def _get_interval_in_second(self):
        options = {'S': 1, 'M': 60, 'H': 3600, 'D': 86400 }
        seconds = options[_get_handler_config_value('file', 'when')]
        return int(_get_handler_config_value('file', 'interval')) * seconds

    def setUp(self):
        self.service = BlobService(ACCOUNT_NAME, ACCOUNT_KEY)
        # ensure that there's no log file in the container before each test
        containers_created = [c.name for c in self.service.list_containers()]
        for handler in LOGGING['handlers']:
            container = self._get_container_name(handler)
            if container:
                if container in containers_created:
                    filename = _get_handler_config_value(handler, 'filename')
                    basename = os.path.basename(filename)
                    for blob in self.service.list_blobs(container, prefix=basename):
                        self.service.delete_blob(container, blob.name)
                else:
                    self.service.create_container(container)

    def test_rotation(self):
        # get the logger for the test
        logger_name = 'file'
        logger = logging.getLogger(logger_name)
        handler_name = _get_handler_name(logger_name)

        # confirm that there's no outdated log file in the container at this point 
        container = self._get_container_name(handler_name)
        filename = _get_handler_config_value(handler_name, 'filename')
        basename = os.path.basename(filename)
        blobs = iter(self.service.list_blobs(container, prefix=basename))
        with self. assertRaises(StopIteration):
            next(blobs)

        # perform logging
        log_text_1 = 'this will be the last line in the rotated log file.'
        logger.info(log_text_1)

        # perform logging again after the interval
        time.sleep(self._get_interval_in_second()+5)
        log_text_2 = 'this will be the first line in the new log file.'
        logger.info(log_text_2)

        # confirm that the outdated log file is saved in the container
        blobs = iter(self.service.list_blobs(container, prefix=basename))
        blob = next(blobs)
        self.assertTrue(blob.name.startswith(basename))
        #blob_text = self.service.get_blob_to_text(container, blob.name)
        blob_text = self.service.get_blob(container, blob.name)
        self.assertRegex(blob_text.decode('utf-8'), log_text_1)

        # confirm that there's no more message in the queue
        with self.assertRaises(StopIteration):
            next(blobs)

        # confirm that the current log file has correct logs
        with open(filename, 'r') as f:
            self.assertRegex(f.readline(), log_text_2)


class QueueStorageHandlerTest(_TestCase):

    def setUp(self):
        self.service = QueueService(ACCOUNT_NAME, ACCOUNT_KEY)
        # ensure that there's no message on the queue before each test
        queues = set()
        for cfg in LOGGING['handlers'].values():
            if 'queue' in cfg:
                queues.add(cfg['queue'])
        for queue in self.service.list_queues():
            if queue.name in queues:
                self.service.clear_messages(queue.name)

    def test_logging(self):
        # get the logger for the test
        logger_name = 'queue'
        logger = logging.getLogger(logger_name)
        handler_name = _get_handler_name(logger_name)

        # confirm that there's no message in the queue at this point
        queue = _get_handler_config_value(handler_name, 'queue')
        messages = iter(self.service.get_messages(queue))
        with self.assertRaises(StopIteration):
            next(messages)

        # perform logging
        log_text = 'logging test'
        logger.info(log_text)

        # confirm that the massage has correct log text
        messages = iter(self.service.get_messages(queue))
        message = next(messages)
        text_expected = "INFO %s" % log_text
        if _get_handler_config_value(handler_name, 'base64_encoding'):
            text_expected = _base64_encode(text_expected)
        self.assertEqual(message.message_text, text_expected)

        # confirm that there's no more message in the queue
        with self.assertRaises(StopIteration):
            next(messages)

    def test_message_ttl(self):
        # get the logger for the test
        logger_name = 'message_ttl'
        logger = logging.getLogger(logger_name)
        handler_name = _get_handler_name(logger_name)

        # confirm that there's no message in the queue at this point
        queue = _get_handler_config_value(handler_name, 'queue')
        messages = iter(self.service.get_messages(queue))
        with self.assertRaises(StopIteration):
            next(messages)

        # perform logging
        log_text = 'time-to-live test'
        logger.info(log_text)

        # confirm that the new message is visible till the ttl expires
        messages = iter(self.service.get_messages(queue))
        message = next(messages)
        text_expected = 'INFO %s' % log_text
        if _get_handler_config_value(handler_name, 'base64_encoding'):
            text_expected = _base64_encode(text_expected)
        self.assertEqual(message.message_text, text_expected)

        # confirm that there's no more message in the queue
        with self.assertRaises(StopIteration):
            next(messages)

        # confirm that the new message is invisible after the ttl expires
        ttl = _get_handler_config_value(handler_name, 'message_ttl')
        time.sleep(int(ttl)+5)
        messages = iter(self.service.get_messages(queue))
        with self.assertRaises(StopIteration):
            next(messages)

    def test_visibility_timeout(self):
        # get the logger for the test
        logger_name = 'visibility_timeout'
        logger = logging.getLogger(logger_name)
        handler_name = _get_handler_name(logger_name)

        # confirm that there's no message in the queue at this point
        queue = _get_handler_config_value(handler_name, 'queue')
        messages = iter(self.service.get_messages(queue))
        with self.assertRaises(StopIteration):
            next(messages)

        # perform logging
        log_text = 'visibility test'
        logger.info(log_text)

        # confirm that the new message is invisible till the timeout expires
        messages = iter(self.service.get_messages(queue))
        with self.assertRaises(StopIteration):
            next(messages)

        # confirm that the new message is visible after the timeout expires
        timeout = _get_handler_config_value(handler_name, 'visibility_timeout')
        time.sleep(int(timeout)+5)
        messages = iter(self.service.get_messages(queue))
        message = next(messages)
        text_expected = 'INFO %s' % log_text
        if _get_handler_config_value(handler_name, 'base64_encoding'):
            text_expected = _base64_encode(text_expected)
        self.assertEqual(message.message_text, text_expected)

        # confirm that there's no more message in the queue
        with self.assertRaises(StopIteration):
            next(messages)

    def test_base64_encoding(self):
        # get the logger for the test
        logger_name = 'base64_encoding'
        logger = logging.getLogger(logger_name)
        handler_name = _get_handler_name(logger_name)

        # confirm that there's no message in the queue at this point
        queue = _get_handler_config_value(handler_name, 'queue')
        messages = iter(self.service.get_messages(queue))
        with self.assertRaises(StopIteration):
            next(messages)

        # perform logging
        log_text = 'Base64 encoding test'
        logger.info(log_text)

        # confirm that the log message is encoded in Base64
        queue = _get_handler_config_value(handler_name, 'queue')
        messages = iter(self.service.get_messages(queue))
        message = next(messages)
        text_expected = "INFO %s" % log_text
        if _get_handler_config_value(handler_name, 'base64_encoding'):
            text_expected = _base64_encode(text_expected)
        self.assertEqual(message.message_text, text_expected)

        # confirm that there's no more message in the queue
        with self.assertRaises(StopIteration):
            next(messages)


class TableStorageHandlerTest(_TestCase):

    def _get_formatter_name(self, handler_name, formatter_type):
        name = _get_handler_config_value(handler_name, formatter_type)
        if name:
            if name.startswith('cfg://formatters.'):
                name = name.split('.')[1]
        return name

    def _get_partition_key_formatter_name(self, handler_name):
        return self._get_formatter_name(handler_name, 'partition_key_formatter')

    def _get_row_key_formatter_name(self, handler_name):
        return self._get_formatter_name(handler_name, 'row_key_formatter')

    def setUp(self):
        self.service = TableService(ACCOUNT_NAME, ACCOUNT_KEY)
        # ensure that there's no entity in the table before each test
        tables = set()
        for cfg in LOGGING['handlers'].values():
            if 'table' in cfg:
                tables.add(cfg['table'])
        for table in self.service.query_tables():
            if table.name in tables:
                for entity in self.service.query_entities(table.name):
                    self.service.delete_entity(table.name,
                                               entity.PartitionKey,
                                               entity.RowKey)

    def test_logging(self):
        # get the logger for the test
        logger_name = 'table'
        logger = logging.getLogger(logger_name)
        handler_name = _get_handler_name(logger_name)

        # confirm that there's no entity in the table at this point
        table = _get_handler_config_value(handler_name, 'table')
        entities = iter(self.service.query_entities(table))
        with self.assertRaises(StopIteration):
            next(entities)

        # perform logging
        log_text = 'logging test'
        logging_started = datetime.now()
        logger.info(log_text)
        logging_finished = datetime.now()

        # confirm that the entity has correct log text
        entities = iter(self.service.query_entities(table))
        entity = next(entities)
        self.assertEqual(entity.message, 'INFO %s' % log_text)

        # confirm that the entity has the default partitiok key
        fmt = '%Y%m%d%H%M'
        try:
            self.assertEqual(entity.PartitionKey, logging_started.strftime(fmt))
        except AssertionError:
            if logging_started == logging_finished:
                raise
            self.assertEqual(entity.PartitionKey, logging_finished.strftime(fmt))

        # confirm that the entity has the default row key
        portions = iter(entity.RowKey.split('-'))
        timestamp = next(portions)
        fmt = '%Y%m%d%H%M%S'
        self.assertGreaterEqual(timestamp[:-3], logging_started.strftime(fmt))
        self.assertLessEqual(timestamp[:-3], logging_finished.strftime(fmt))
        self.assertRegex(timestamp[-3:], '^[0-9]{3}$')
        self.assertEqual(next(portions), gethostname())
        self.assertEqual(int(next(portions)), os.getpid())
        self.assertEqual(next(portions), '00')
        with self.assertRaises(StopIteration):
            next(portions)

        # confirm that there's no more entity in the table
        with self.assertRaises(StopIteration):
            next(entities)

    @unittest.skipIf(_EMULATED, "Azure Storage Emulator doesn't support batch operation.")
    def test_batch(self):
        # get the logger for the test
        logger_name = 'batch'
        logger = logging.getLogger(logger_name)
        handler_name = _get_handler_name(logger_name)

        # confirm that there's no entity in the table at this point
        table = _get_handler_config_value(handler_name, 'table')
        entities = iter(self.service.query_entities(table))
        with self.assertRaises(StopIteration):
            next(entities)

        # perform logging and execute  the first batch
        batch_size = _get_handler_config_value(handler_name, 'batch_size')
        log_text = 'batch logging test'
        for i in range(batch_size + int(batch_size/2)):
            logger.info('%s#%02d' % (log_text, i))

        # confirm that only batch_size entities are committed at this point
        entities = list(iter(self.service.query_entities(table)))
        self.assertEqual(len(entities), batch_size)
        rowno_found = set()
        seq_found = set()
        for entity in entities:
            # partition key
            self.assertEqual(entity.PartitionKey, 'batch-%s' % gethostname())
            # row key
            rowno = entity.RowKey.split('-')[-1]
            self.assertLess(int(rowno), batch_size)
            self.assertNotIn(rowno, rowno_found)
            rowno_found.add(rowno)
            # message
            message, seq = entity.message.split('#')
            self.assertEqual(message, 'INFO %s' % log_text)
            self.assertLess(int(seq), batch_size)
            self.assertNotIn(seq, seq_found)
            seq_found.add(seq)

        # remove currently created entities before the next batch
        for entity in entities:
            self.service.delete_entity(table,
                                       entity.PartitionKey,
                                       entity.RowKey)

        # perform logging again and execute the next batch
        for j in range(i+1, int(batch_size/2)+i+1):
            logger.info('%s#%02d' % (log_text, j))

        # confirm that the remaining entities are committed in the next batch
        entities = list(iter(self.service.query_entities(table)))
        self.assertEqual(len(entities), batch_size)
        rowno_found.clear()
        for entity in entities:
            # partition key
            self.assertEqual(entity.PartitionKey, 'batch-%s' % gethostname())
            # row key
            rowno = entity.RowKey.split('-')[-1]
            self.assertLess(int(rowno), batch_size)
            self.assertNotIn(rowno, rowno_found)
            rowno_found.add(rowno)
            # message
            message, seq = entity.message.split('#')
            self.assertEqual(message, 'INFO %s' % log_text)
            self.assertGreaterEqual(int(seq), batch_size)
            self.assertLess(int(seq), batch_size*2)
            self.assertNotIn(seq, seq_found)
            seq_found.add(seq)

    def test_extra_properties(self):
        # get the logger for the test
        logger_name = 'extra_properties'
        logger = logging.getLogger(logger_name)
        handler_name = _get_handler_name(logger_name)
        
        # confirm that there's no entity in the table at this point
        table = _get_handler_config_value(handler_name, 'table')
        entities = iter(self.service.query_entities(table))
        with self.assertRaises(StopIteration):
            next(entities)

        # perform logging
        log_text = 'extra properties test'
        logger.info(log_text)

        # confirm that the entity has correct log text
        entities = iter(self.service.query_entities(table))
        entity = next(entities)
        self.assertEqual(entity.message, 'INFO %s' % log_text)

        # confirm that the extra properties have correct values
        table = _get_handler_config_value(handler_name, 'table')
        entity = next(iter(self.service.query_entities(table)))
        self.assertEqual(entity.hostname, gethostname())
        self.assertEqual(entity.levelname, 'INFO')
        self.assertEqual(int(entity.levelno), logging.INFO)
        self.assertEqual(entity.module, os.path.basename(__file__).rpartition('.')[0])
        self.assertEqual(entity.name, logger_name)
        self.assertEqual(int(entity.process), os.getpid())
        self.assertEqual(int(entity.thread), current_thread().ident)

        # confirm that there's no more entity in the table
        with self.assertRaises(StopIteration):
            next(entities)

    def test_custom_key_formatters(self):
        # get the logger for the test
        logger_name = 'custom_keys'
        logger = logging.getLogger(logger_name)
        handler_name = _get_handler_name(logger_name)

        # confirm that there's no entity in the table at this point
        table = _get_handler_config_value(handler_name, 'table')
        entities = iter(self.service.query_entities(table))
        with self.assertRaises(StopIteration):
            next(entities)

        # perform logging
        log_text = 'custom key formatters test'
        logging_started = datetime.now()
        logger.info(log_text)
        logging_finished = datetime.now()

        # confirm that the entity correct log text
        table = _get_handler_config_value(handler_name, 'table')
        entities = iter(self.service.query_entities(table))
        entity = next(entities)
        self.assertEqual(entity.message, 'INFO %s' % log_text)

        # confirm that the entity has a custom partitiok key
        portions = iter(entity.PartitionKey.split('-'))
        self.assertEqual(next(portions), 'mycustompartitionkey')
        self.assertEqual(next(portions), gethostname())
        formatter_name = self._get_partition_key_formatter_name(handler_name)
        fmt = _get_formatter_config_value(formatter_name, 'datefmt')
        asctime = next(portions)
        try:
            self.assertEqual(asctime, logging_started.strftime(fmt))
        except AssertionError:
            if logging_started == logging_finished:
                raise
            self.assertEqual(asctime, logging_finished.strftime(fmt))
        with self.assertRaises(StopIteration):
            next(portions)

        # confirm that the entity has a custom row key
        portions = iter(entity.RowKey.split('-'))
        self.assertEqual(next(portions), 'mycustomrowkey')
        self.assertEqual(next(portions), gethostname())
        formatter_name = self._get_row_key_formatter_name(handler_name)
        fmt = _get_formatter_config_value(formatter_name, 'datefmt')
        asctime = next(portions)
        try:
            self.assertEqual(asctime, logging_started.strftime(fmt))
        except AssertionError:
            if logging_started == logging_finished:
                raise
            self.assertEqual(asctime, logging_finished.strftime(fmt))
        with self.assertRaises(StopIteration):
            next(portions)

        # confirm that there's no more entity in the table
        with self.assertRaises(StopIteration):
            next(entities)


if __name__ == '__main__':
    try:
        dictConfig(LOGGING)
        unittest.main()
    finally:
        logging.shutdown()
        rmtree(_LOGFILE_TMPDIR, ignore_errors=True)
