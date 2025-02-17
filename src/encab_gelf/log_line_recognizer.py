from typing import Dict, Optional
from abc import ABC, abstractmethod
from enum import Enum

from logging import getLogger, DEBUG

import re
from grok import GrokPattern  # type: ignore

mylogger = getLogger(__name__)
mylogger.setLevel(DEBUG)


class LogLevel(Enum):
    CRITICAL = 50
    EMERGENCY = CRITICAL
    ALERT = CRITICAL
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10

    @classmethod
    def levelsByName(cls) -> Dict[str, "LogLevel"]:
        return {
            "EMERGENCY": cls.EMERGENCY,
            "ALERT": cls.ALERT,
            "CRITICAL": cls.CRITICAL,
            "FATAL": cls.FATAL,
            "ERROR": cls.ERROR,
            "WARN": cls.WARNING,
            "WARNING": cls.WARNING,
            "INFO": cls.INFO,
            "DEBUG": cls.DEBUG,
        }

    @classmethod
    def namesBylevel(cls) -> Dict["LogLevel", str]:
        return {
            cls.CRITICAL: "CRITICAL",
            cls.ERROR: "ERROR",
            cls.WARNING: "WARNING",
            cls.INFO: "INFO",
            cls.DEBUG: "DEBUG",
        }

    @classmethod
    def fromString(cls, s: str) -> Optional["LogLevel"]:
        level = cls.levelsByName().get(s.upper(), 0)
        return LogLevel(level) if level else None

    @classmethod
    def levelPattern(cls) -> re.Pattern:
        names = cls.levelsByName().keys()
        pattern = "|".join([name for name in names])
        return re.compile(f"({pattern})", re.IGNORECASE)


class LogLine(object):
    def __init__(
        self,
        line: str,
        level: Optional[LogLevel] = None,
        attrs: Optional[Dict[str, str]] = None,
    ) -> None:
        self.level = level
        self.line = line
        self.attrs = attrs or dict()


class LogLineRecognizer(ABC):
    @abstractmethod
    def recognize(self, line: str) -> LogLine:
        pass


class GrokRecognizer(LogLineRecognizer):
    def __init__(self, pattern: str, log_level_tag: str = "LOGLEVEL") -> None:
        self.pattern = GrokPattern(pattern)
        self.log_level_tag = log_level_tag

    def recognize(self, line: str) -> LogLine:
        match = self.pattern.regex.match(line)
        attrs = match.groupdict() if match else dict()
        attrs = {k: v for k, v in attrs.items() if k != self.log_level_tag}
        levelName = attrs.get(self.log_level_tag, 0)
        level = LogLevel.fromString(levelName) if levelName else None
        return LogLine(line, level, attrs)


class NoMatch(Exception):
    pass


class DefaultRecognizer(LogLineRecognizer):
    def __init__(self) -> None:
        self.levelPattern = LogLevel.levelPattern()

    def isNoLogLine(self, s: str) -> bool:
        return len(s) <= 1 and not (s[0].isalnum() or s[0] in ["[", "{", "|"])

    def recognize(self, line: str) -> LogLine:
        try:
            if self.isNoLogLine(line):
                raise NoMatch()

            match: Optional[re.Match[str]] = self.levelPattern.match(line)
            if not match:
                raise NoMatch()

            levelName = match.group(1)
            level = LogLevel.fromString(levelName) if levelName else None
            return LogLine(line, level)
        except NoMatch:
            return LogLine(line)
