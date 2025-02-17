import yaml
import marshmallow_dataclass
import json

from typing import Dict, Any, Optional
from logging import getLogger

from dataclasses import dataclass, field
from marshmallow.exceptions import MarshmallowError, ValidationError
from abc import ABC

ENCAB = "encab"
ENCAB_GELF = "encab_gelf"

mylogger = getLogger(ENCAB_GELF)


class ConfigError(ValueError):
    pass


@dataclass
class RecognizerSettings(ABC):
    type: str = field(default="default")
    # recognizer ``default`` or ``grok`` or ``json``
    pattern: Optional[str] = field(default=None)
    # grok pattern if ``type == 'grok'``
    #
    # see: https://pypi.org/project/pygrok/


@dataclass
class GelfHandlerSettings(ABC):
    protocol: str
    # GELF Protocol. One of HTTP, HTTPS, UDP, TCP, TLS
    host: str
    # Graylog input host or IP address (default=localhost)
    port: int = field(default=12201)
    # Graylog port (default=12201)
    optional_fields: Dict[str, Any] = field(default_factory=lambda: dict())
    # optional gelf fields as dictionary. Will be added to each log record.
    enabled: bool = field(default=True)
    # True - the handler is enabled (default), False - the handler is disabled

    # -- HTTP

    path: str = field(default="/gelf")
    # ('/gelf' by default) - path of the HTTP input
    compress: bool = field(default=True)
    # (True by default) - if true, compress log messages before sending them to the server
    timeout: float = field(default=5.0)
    # (5 by default) - amount of seconds that HTTP client should wait before it discards the request if the server doesn't respond

    # -- UDP

    # (True by default) - if true, compress log messages before sending them to the server
    chunk_size: int = field(default=1300)
    # (1300 by default) - maximum length of the message. If log length exceeds this value, it splits into multiple chunks

    # -- HTTPS

    validate: bool = field(default=False)
    # if true, validate server certificate. In that case ca_certs are required
    ca_certs: Optional[str] = field(default=None)
    # path to CA bundle file. For instance, on CentOS it would be '/etc/pki/tls/certs/ca-bundle.crt'

    # -- TLS

    # path to CA bundle file. For instance, on CentOS it would be '/etc/pki/tls/certs/ca-bundle.crt'
    certfile: Optional[str] = field(default=None)
    # path to the certificate file that is used to identify ourselves to the server
    keyfile: Optional[str] = field(default=None)
    # path to the private key. If the private key is stored with the certificate, this parameter can be ignored

    recognizer: RecognizerSettings = field(default_factory=lambda: RecognizerSettings())
    # log line recognizer settings


@dataclass
class GelfSettings(object):
    """
    the Graylog/GELF settings

    example:

    .. code-block:: yaml

        encab:
            debug: true
            halt_on_exit: False
        extensions:
            gelf:
                module: encab_gelf
                enabled: true
                settings:
                    handlers:
                        HTTP:
                            protocol: HTTP
                            host: localhost # host name or IP address of the GELF input
                            port: 80        # port of the GELF input
                            optional_fields: # optional fields added to each log record
                                localname: encab
    """

    GRAYLOG_ENABLED = "GRAYLOG_ENABLED"
    GRAYLOG_PROTOCOL = "GRAYLOG_PROTOCOL"
    GRAYLOG_HOST = "GRAYLOG_HOST"
    GRAYLOG_PORT = "GRAYLOG_PORT"
    GRAYLOG_OPTIONAL_FIELDS = "GRAYLOG_OPTIONAL_FIELDS"

    handlers: Dict[str, GelfHandlerSettings]

    def update_default_handler(self, environment: Dict[str, Any]) -> None:
        set_default_handler = False
        for var in [
            self.GRAYLOG_ENABLED,
            self.GRAYLOG_PROTOCOL,
            self.GRAYLOG_HOST,
            self.GRAYLOG_PORT,
            self.GRAYLOG_OPTIONAL_FIELDS,
        ]:
            if var in environment:
                set_default_handler = True
                break

        if set_default_handler:
            is_enabled = environment.get(self.GRAYLOG_ENABLED, 1) in ("True", "true", 1)
            optional_fields_var = environment.get(self.GRAYLOG_OPTIONAL_FIELDS)
            optional_fields = dict()
            if optional_fields_var:
                try:
                    optional_fields = json.loads(optional_fields_var)
                    assert isinstance(optional_fields, dict)
                except Exception as e:
                    raise ConfigError(
                        f"Error parsing environment variable {self.GRAYLOG_OPTIONAL_FIELDS}: {str(e)}"
                    )

            if "default" not in self.handlers:
                protocol = environment.get(self.GRAYLOG_PROTOCOL, "HTTP")
                host = environment.get(self.GRAYLOG_HOST, "localhost")
                port = int(environment.get(self.GRAYLOG_PORT, 12201))
                self.handlers["default"] = GelfHandlerSettings(
                    protocol, host, port, optional_fields, is_enabled
                )
                mylogger.info(
                    "Added default GELF handler from environment: %s",
                    str(self.handlers["default"]),
                    extra={"program": ENCAB_GELF},
                )
            else:
                handler = self.handlers["default"]
                handler.enabled = is_enabled
                handler.protocol = environment.get(
                    self.GRAYLOG_PROTOCOL, handler.protocol
                )
                handler.host = environment.get(self.GRAYLOG_HOST, handler.host)
                handler.port = int(environment.get(self.GRAYLOG_PORT, handler.port))
                handler.optional_fields = (
                    optional_fields if optional_fields_var else handler.optional_fields
                )
                mylogger.info(
                    "Added default GELF handler from environment: %s",
                    str(handler),
                    extra={"program": ENCAB_GELF},
                )

    @staticmethod
    def load(settings: Dict[str, Any]) -> "GelfSettings":
        try:
            ConfigSchema = marshmallow_dataclass.class_schema(GelfSettings)
            settings = ConfigSchema().load(settings)  # type: ignore
            assert isinstance(settings, GelfSettings)
            return settings
        except ValidationError as e:
            msg = e.args[0]
            if isinstance(msg, dict):
                msg = yaml.dump(msg, default_flow_style=False)

            raise ConfigError(f"\n\n{ENCAB_GELF}:\n{msg}")
        except MarshmallowError as e:
            raise ConfigError(e.args)
