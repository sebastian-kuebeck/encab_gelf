from typing import Dict, Any, List, Optional

from logging import LogRecord, getLogger, Handler, DEBUG
from http.client import HTTPException

from .one_shot_timer import OneShotTimer
from .log_line_recognizer import LogLineRecognizer, DefaultRecognizer

from socket import error as SocketError

ENCAB = "encab"
ENCAB_GELF = "encab_gelf"

mylogger = getLogger(__name__)
mylogger.setLevel(DEBUG)


class ExtLogRecord(LogRecord):
    def __init__(self, record: LogRecord) -> None:
        super().__init__(
            record.name,
            record.levelno,
            record.pathname,
            record.lineno,
            record.msg,
            record.args,
            record.exc_info,
            record.funcName,
            record.stack_info,
        )
        self.is_log_record = True
        self.extra: Dict[str, Any] = (
            record.extra
            if hasattr(record, "extra") and isinstance(record.extra, dict)
            else {}
        )

        self.suppress = self.extra.get("suppress", False)
        self.program = self.extra.get("program")
        self.is_from_encab = self.program in (ENCAB, ENCAB_GELF)

    @staticmethod
    def fromRecord(record: LogRecord) -> "ExtLogRecord":
        return record if isinstance(record, ExtLogRecord) else ExtLogRecord(record)

    def getMessage(self):
        msg = str(self.msg)
        try:
            if self.args:
                msg = msg % self.args
        except TypeError:
            pass
        return msg


class MultiLineHandler(Handler):
    TIMEOUT: float = 0.5

    def __init__(
        self, name: str, handler: Handler, timeout: Optional[float] = None
    ) -> None:
        super().__init__(handler.level)
        self.name = name
        self.handler = handler
        self.backlog: List[LogRecord] = list()
        self.timer = OneShotTimer(timeout or self.TIMEOUT, self.flush)

    def emit_upstream(self, record: LogRecord):
        self.handler.emit(record)

    def emitAll(self, record: LogRecord):
        self.timer.clear()
        self.flush()
        self.emit_upstream(record)

    def emit(self, log_record: LogRecord) -> None:
        record = ExtLogRecord.fromRecord(log_record)

        if not self.backlog:
            self.backlog.append(record)
            self.timer.start()
            return

        first_record = self.backlog[0]

        if (
            first_record.name == record.name
            and first_record.levelno == record.levelno
            and first_record.thread == record.thread
            and not first_record.args
            and not record.is_log_record
        ):
            self.backlog.append(record)
        else:
            return self.emitAll(record)

    def flush(self):
        if self.backlog:
            first_record = self.backlog[0]
            lines = [first_record.getMessage()]
            for record in self.backlog[1:]:
                lines.append(record.getMessage())
            first_record.msg = "\n".join(lines)
            self.emit_upstream(first_record)
            self.backlog = list()

    def close(self):
        self.timer.close()
        self.flush()


class RecognizingHandler(Handler):
    def __init__(
        self,
        handler: Handler,
        handler_name: str,
        recognizer: Optional[LogLineRecognizer] = None,
    ) -> None:
        super().__init__(handler.level)
        self.recognizer = recognizer or DefaultRecognizer()
        self.handler = handler
        self.handler_name: str = handler_name

    def recognize(self, record: ExtLogRecord) -> ExtLogRecord:
        log_line = self.recognizer.recognize(record.getMessage())
        record.is_log_record = log_line.level is not None

        if not record.is_log_record:
            return record

        assert log_line.level

        record.levelno = log_line.level.value
        record.levelname = log_line.level.name
        record.extra = {**record.extra, **log_line.attrs}
        return record

    def emit(self, log_record: LogRecord) -> None:
        record = ExtLogRecord.fromRecord(log_record)

        if record.args or record.suppress or record.is_from_encab:
            return self.handler.emit(record)

        self.handler.emit(self.recognize(record))


class ErrorHandler(Handler):
    def __init__(self, handler: Handler, handler_name: str, host_url: str) -> None:
        super().__init__(handler.level)
        self.handler = handler
        self.errors: int = 0
        self.handler_name: str = handler_name
        self.host_url = host_url

    def emit(self, log_record: LogRecord) -> None:
        record = ExtLogRecord.fromRecord(log_record)

        if record.suppress:
            return

        try:
            self.handler.emit(record)
            if self.errors:
                self.errors = 0
        except (HTTPException, ConnectionError, SocketError) as e:
            if not self.errors:
                mylogger.warning(
                    "GELF Handler %s failed to connect to %s: %s",
                    self.handler_name,
                    self.host_url,
                    str(e),
                    extra={"program": ENCAB_GELF, "suppress": True},
                )
            else:
                self.errors = (self.errors + 1) % 100
        except Exception as e:
            mylogger.exception(
                "GELF Handler %s connecting to %s: %s",
                self.handler_name,
                self.host_url,
                str(e),
                extra={"program": ENCAB_GELF, "suppress": True},
            )
