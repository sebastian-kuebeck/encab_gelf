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
            f"Configuring GELF filter {name}: {str(settings)}",
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
            recognizers = RecognizerFactory(settings.recognizer)
            yield MultiLineHandler(
                name,
                RecognizingHandler(
                    ErrorHandler(self.create(name, settings), name),
                    name,
                    recognizers.create(),
                ),
            )


extension_impl = HookimplMarker(ENCAB)

is_enabled: bool = False

gelf_settings: Optional[GelfSettings] = None

factory: Optional[GelfLogHandlerFactory] = None


@extension_impl
def validate_extension(name: str, enabled: bool, settings: Dict[str, Any]):
    if name != ENCAB_GELF:
        return

    if not enabled:
        return

    gelf_settings = GelfSettings.load(settings)
    GelfLogHandlerFactory(gelf_settings)


@extension_impl
def configure_extension(name: str, enabled: bool, settings: Dict[str, Any]):
    global gelf_settings, factory, is_enabled

    if name != ENCAB_GELF:
        return

    is_enabled = enabled
    if not enabled:
        return

    gelf_settings = GelfSettings.load(settings)
    factory = GelfLogHandlerFactory(gelf_settings)


@extension_impl
def extend_environment(program_name: str, environment: Dict[str, str]):
    global gelf_settings, factory, is_enable

    if program_name == ENCAB:
        assert gelf_settings
        assert factory

        if "GRAYLOG_ENABLED" in environment:
            is_enabled = environment["GRAYLOG_ENABLED"] in ("True", "true", 1)

        if not is_enabled:
            return

        gelf_settings = GelfSettings.update_default_handler(gelf_settings, environment)
        factory.update_settings(gelf_settings)


@extension_impl
def update_logger(program_name: str, logger: Logger):
    global is_enable

    if program_name == ENCAB:
        return

    if not is_enabled:
        return

    if not factory:
        return

    mylogger.info("Adding GELF Handlers", extra={"program": ENCAB_GELF})

    for hander in factory.createAll():
        logger.addHandler(hander)
