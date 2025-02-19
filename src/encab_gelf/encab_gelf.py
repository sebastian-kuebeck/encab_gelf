from typing import Dict, Any, Optional, Iterator

from logging import getLogger, Logger, Handler, DEBUG
from pluggy import HookimplMarker  # type: ignore

from .log_line_recognizer import LogLineRecognizer, DefaultRecognizer, GrokRecognizer
from .handlers import (
    MultiLineHandler,
    ErrorHandler,
    RecognizingHandler,
    ENCAB,
    ENCAB_GELF,
)

from .gelf.handlers import (
    GelfHttpHandler,
    GelfUdpHandler,
    GelfHttpsHandler,
    GelfTcpHandler,
    GelfTlsHandler,
)

from .config import RecognizerSettings, GelfHandlerSettings, GelfSettings, ConfigError

mylogger = getLogger(ENCAB_GELF)
mylogger.setLevel(DEBUG)


class RecognizerFactory(object):
    def __init__(self, settings: RecognizerSettings) -> None:
        self.settings = settings

    def create(self) -> LogLineRecognizer:
        if self.settings.type == "default":
            return DefaultRecognizer()
        elif self.settings.type == "grok":
            if not self.settings.pattern:
                raise ConfigError("Missing Grok regcognizer pattern")
            return GrokRecognizer(self.settings.pattern)
        else:
            raise ConfigError(f"Unsupported recognizer {self.settings.type}")


class GelfLogHandlerFactory(object):
    def __init__(self, gelf_settings: GelfSettings) -> None:
        self.gelf_settings = gelf_settings

    def update_settings(self, gelf_settings: GelfSettings) -> None:
        self.gelf_settings = gelf_settings

    def create(self, name: str, settings: GelfHandlerSettings):
        mylogger.info(
            f"Configuring GELF filter {name}: {settings.log_info()}",
            extra={"program": ENCAB_GELF},
        )
        assert settings.protocol in ["HTTP", "HTTPS", "UDP", "TCP", "TLS"]
        if settings.protocol == "HTTP":
            return GelfHttpHandler(
                host=settings.host,
                port=settings.port,
                compress=settings.compress,
                path=settings.path,
                timeout=settings.timeout,
                **settings.optional_fields,
            )
        elif settings.protocol == "HTTPS":
            return GelfHttpsHandler(
                host=settings.host,
                port=settings.port,
                compress=settings.compress,
                path=settings.path,
                timeout=settings.timeout,
                validate=settings.validate,
                ca_certs=settings.ca_certs,
                **settings.optional_fields,
            )
        elif settings.protocol == "UDP":
            return GelfUdpHandler(
                host=settings.host,
                port=settings.port,
                compress=settings.compress,
                chunk_size=settings.chunk_size,
                **settings.optional_fields,
            )
        elif settings.protocol == "TCP":
            return GelfTcpHandler(
                host=settings.host, port=settings.port, **settings.optional_fields
            )
        elif settings.protocol == "TLS":
            return GelfTlsHandler(
                host=settings.host,
                port=settings.port,
                validate=settings.validate,
                ca_certs=settings.ca_certs,
                certfile=settings.certfile,
                keyfile=settings.keyfile,
                **settings.optional_fields,
            )

    def createAll(self) -> Iterator[Handler]:
        for name, settings in self.gelf_settings.handlers.items():
            if not settings.enabled:
                continue

            recognizers = RecognizerFactory(settings.recognizer)
            yield MultiLineHandler(
                name,
                RecognizingHandler(
                    ErrorHandler(
                        self.create(name, settings), name, settings.host_url()
                    ),
                    name,
                    recognizers.create(),
                ),
            )


extension_impl = HookimplMarker(ENCAB)


class GelfExtension:
    def __init__(self) -> None:
        self.settings: Optional[GelfSettings] = None
        self.factory: Optional[GelfLogHandlerFactory] = None

    def validate_settings(self, settings: Dict[str, Any]) -> None:
        GelfSettings.load(settings)

    def update_settings(self, settings: Dict[str, Any]) -> None:
        self.settings = GelfSettings.load(settings)
        self.factory = GelfLogHandlerFactory(self.settings)

    def update_from_environment(self, environment: Dict[str, str]) -> None:
        assert self.factory
        assert self.settings
        self.settings.update_default_handler(environment)

    def is_enabled(self) -> bool:
        return self.settings is not None


extension = GelfExtension()


@extension_impl
def validate_extension(name: str, enabled: bool, settings: Dict[str, Any]):
    global extension

    if name != ENCAB_GELF:
        return

    if not enabled:
        return

    extension.validate_settings(settings)


@extension_impl
def configure_extension(name: str, enabled: bool, settings: Dict[str, Any]):
    global extension

    if name != ENCAB_GELF:
        return

    if not enabled:
        return

    from os import environ

    is_enabled = environ.get(GelfSettings.GRAYLOG_ENABLED, 1) in ("True", "true", 1)

    if not is_enabled:
        return

    extension.update_settings(settings)
    extension.update_from_environment(dict(environ))


@extension_impl
def update_logger(program_name: str, logger: Logger):
    global extension

    if program_name == ENCAB:
        return

    if not extension.is_enabled():
        return

    mylogger.info("Adding GELF Handlers", extra={"program": ENCAB_GELF})

    assert extension.factory
    for hander in extension.factory.createAll():
        logger.addHandler(hander)
