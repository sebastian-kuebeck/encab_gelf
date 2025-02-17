import unittest
import os


from encab_gelf.config import GelfSettings
from encab_gelf.encab_gelf import extension, configure_extension, ENCAB_GELF


class EncabGelfTest(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def testConfigureExtension(self):
        settings_data = {
            "handlers": {
                "default": {
                    "enabled": True,
                    "protocol": "HTTP",
                    "host": "localhost",
                    "port": 11201,
                    "optional_fields": {"localname": "encab"},
                }
            }
        }

        os.environ = dict()
        configure_extension(ENCAB_GELF, True, settings_data)

        settings = extension.settings

        assert isinstance(settings, GelfSettings)
        self.assertEqual(1, len(settings.handlers))
        handler = settings.handlers["default"]
        self.assertEqual("HTTP", handler.protocol)
        self.assertEqual("localhost", handler.host)
        self.assertEqual(11201, handler.port)
        self.assertEqual({"localname": "encab"}, handler.optional_fields)
        self.assertEqual(True, handler.enabled)

    def testExtendEnvironment(self):
        global extension

        settings_data = {
            "handlers": {
                "default": {
                    "enabled": False,
                    "protocol": "HTTP",
                    "host": "localhost",
                    "port": 11201,
                    "optional_fields": {"localname": "encab"},
                }
            }
        }

        environment = {
            GelfSettings.GRAYLOG_ENABLED: "True",
            GelfSettings.GRAYLOG_PROTOCOL: "UDP",
            GelfSettings.GRAYLOG_HOST: "127.0.0.2",
            GelfSettings.GRAYLOG_PORT: "12121",
            GelfSettings.GRAYLOG_OPTIONAL_FIELDS: '{"localname": "encab2"}',
        }

        os.environ.update(environment)

        configure_extension(ENCAB_GELF, True, settings_data)

        settings = extension.settings

        self.assertEqual(1, len(settings.handlers))
        handler = settings.handlers["default"]
        self.assertEqual("UDP", handler.protocol)
        self.assertEqual("127.0.0.2", handler.host)
        self.assertEqual(12121, handler.port)
        self.assertEqual({"localname": "encab2"}, handler.optional_fields)
        self.assertEqual(True, handler.enabled)
