import unittest
import time

from typing import List, Tuple, Optional, Any, Dict
from logging import Handler, LogRecord, INFO, ERROR
from encab_gelf.handlers import (
    ExtLogRecord,
    MultiLineHandler,
    ErrorHandler,
    RecognizingHandler,
    mylogger,
)


class TestHandler(Handler):
    def __init__(self, level: int | str = 0) -> None:
        super().__init__(level)
        self.records: List[Tuple[str, str, Dict[str, Any]]] = list()
        self.exception: Optional[Exception] = None

    def emit(self, log_record: LogRecord) -> None:
        if self.exception:
            raise self.exception

        record = ExtLogRecord.fromRecord(log_record)
        self.records.append((record.levelname, self.format(record), record.extra))


class MultiLineHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.test_handler = TestHandler()
        self.handler = MultiLineHandler("test", self.test_handler)

    def record(self, level: int, msg: str, is_log_line: bool = True) -> LogRecord:
        log_record = LogRecord(
            "test", level, "tests/unit/gelf_test.py", 24, msg, None, None
        )
        record = ExtLogRecord.fromRecord(log_record)
        record.is_log_record = is_log_line
        return record

    def test_emit(self):
        self.handler.emit(self.record(INFO, "Test Message1"))
        self.handler.emit(self.record(INFO, "Test Message2"))
        self.assertEqual(
            [("INFO", "Test Message1", {}), ("INFO", "Test Message2", {})],
            self.test_handler.records,
        )

    def test_emit_multiline(self):
        self.handler.emit(self.record(INFO, "Test Message1"))
        self.handler.emit(self.record(INFO, " Test Submessage1", False))
        self.handler.emit(self.record(INFO, " Test Submessage2", False))
        self.handler.emit(self.record(INFO, "Test Message2"))

        self.assertEqual(
            [
                ("INFO", "Test Message1\n Test Submessage1\n Test Submessage2", {}),
                ("INFO", "Test Message2", {}),
            ],
            self.test_handler.records,
        )

    def test_emit_delayed(self):
        self.handler.emit(self.record(INFO, "Test Message1"))
        self.handler.emit(self.record(INFO, " Test Submessage1", False))
        self.handler.emit(self.record(INFO, " Test Submessage2", False))
        time.sleep(MultiLineHandler.TIMEOUT + 0.1)
        self.assertEqual(
            [("INFO", "Test Message1\n Test Submessage1\n Test Submessage2", {})],
            self.test_handler.records,
        )


class RecognizingHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.test_handler = TestHandler()
        self.handler = RecognizingHandler(self.test_handler, "test")

        self.test_handler2 = TestHandler()
        mylogger.addHandler(self.test_handler2)

    def record(
        self, level: int, msg: str, extra: Optional[Dict[str, Any]] = None
    ) -> LogRecord:
        record = LogRecord(
            "test", level, "tests/unit/gelf_test.py", 24, msg, None, None
        )
        if extra:
            record.extra = extra
        return record

    def ext_record(
        self, level: int, msg: str, extra: Optional[Dict[str, Any]] = None
    ) -> ExtLogRecord:
        return ExtLogRecord(self.record(level, msg, extra))

    def test_recognize(self):
        record = self.handler.recognize(self.ext_record(INFO, "ERROR failed", {"X": 1}))
        self.assertTrue(record.is_log_record)
        self.assertEqual(ERROR, record.levelno)
        self.assertEqual({"X": 1}, record.extra)

    def test_recognize_fail(self):
        record = self.handler.recognize(self.ext_record(INFO, " stack trace", {"X": 1}))
        self.assertFalse(record.is_log_record)
        self.assertEqual(INFO, record.levelno)
        self.assertEqual({"X": 1}, record.extra)

    def test_emit(self):
        self.handler.emit(self.record(INFO, "Test Message1"))
        self.assertEqual(
            [("INFO", "Test Message1", {})],
            self.test_handler.records,
        )


class ErrorHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.test_handler = TestHandler()
        self.handler = ErrorHandler(self.test_handler, "test", "localhost")

        self.test_handler2 = TestHandler()
        mylogger.addHandler(self.test_handler2)

    def record(self, level: int, msg: str) -> LogRecord:
        return LogRecord("test", level, "tests/unit/gelf_test.py", 24, msg, None, None)

    def test_emit(self):
        self.handler.emit(self.record(INFO, "Test Message1"))
        self.assertEqual(
            [("INFO", "Test Message1", {})],
            self.test_handler.records,
        )

    def test_exception_in_emit(self):
        self.test_handler.exception = RuntimeError("Expected Error")
        self.handler.emit(self.record(INFO, "Test Message1"))
        record = self.test_handler2.records[0]
        self.assertEqual(
            "ERROR",
            record[0],
        )
        self.assertEqual(
            "GELF Handler test connecting to localhost: Expected Error",
            record[1].split("\n")[0],
        )
