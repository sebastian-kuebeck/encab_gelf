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

    recognizer: RecognizerSettings = field(default=RecognizerSettings())
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
                            optional_fields: # optiona fields added to each log record 
                                localname: encab
    """

    handlers: Dict[str, GelfHandlerSettings]

    @staticmethod
    def update_default_handler(
        settings: "GelfSettings", environment: Dict[str, Any]
    ) -> "GelfSettings":

        GRAYLOG_PROTOCOL = "GRAYLOG_PROTOCOL"
        GRAYLOG_HOST = "GRAYLOG_HOST"
        GRAYLOG_PORT = "GRAYLOG_PORT"
        GRAYLOG_OPTIONAL_FIELDS = "GRAYLOG_OPTIONAL_FIELDS"

        set_default_handler = False
        for var in [
            GRAYLOG_PROTOCOL,
            GRAYLOG_HOST,
            GRAYLOG_PORT,
            GRAYLOG_OPTIONAL_FIELDS,
        ]:
            if var in environment:
                set_default_handler = True
                break

        if set_default_handler:
            optional_fields_var = environment.get(GRAYLOG_OPTIONAL_FIELDS)
            optional_fields = dict()
            if optional_fields_var:
                try:
                    optional_fields = json.loads(optional_fields_var)
                    assert isinstance(optional_fields, dict)
                except Exception as e:
                    raise ConfigError(
                        f"Error parsing environment variable {GRAYLOG_OPTIONAL_FIELDS}: {str(e)}"
                    )

            if "default" not in settings.handlers:
                protocol = environment.get(GRAYLOG_PROTOCOL, "HTTP")
                host = environment.get(GRAYLOG_HOST, "localhost")
                port = environment.get(GRAYLOG_PORT, 12201)
                settings.handlers["default"] = GelfHandlerSettings(
                    protocol, host, port, optional_fields
                )
            else:
                handler = settings.handlers["default"]
                handler.protocol = environment.get(GRAYLOG_PROTOCOL, handler.protocol)
                handler.host = environment.get(GRAYLOG_HOST, handler.host)
                handler.port = environment.get(GRAYLOG_PORT, handler.port)
                handler.optional_fields = (
                    optional_fields if optional_fields_var else handler.optional_fields
                )

        return settings

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
