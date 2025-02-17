import unittest


from encab_gelf.config import GelfSettings


class GelfSettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def testSettings(self):
        settings_data = {
            "handlers": {
                "default": {
                    "protocol": "HTTP",
                    "host": "localhost",
                    "port": 11201,
                    "optional_fields": {"localname": "encab"},
                }
            }
        }

        settings = GelfSettings.load(settings_data)
        self.assertEqual(1, len(settings.handlers))
        handler = settings.handlers["default"]
        self.assertEqual("HTTP", handler.protocol)
        self.assertEqual("localhost", handler.host)
        self.assertEqual(11201, handler.port)
        self.assertEqual({"localname": "encab"}, handler.optional_fields)
        self.assertEqual(True, handler.enabled)

    def testAddHandlerEnvironment(self):
        settings_data = {
            "handlers": {
                "HTTP": {
                    "enabled": False,
                    "protocol": "HTTP",
                    "host": "localhost",
                    "port": 11201,
                    "optional_fields": {"localname": "encab"},
                }
            }
        }

        settings = GelfSettings.load(settings_data)

        environment = {
            GelfSettings.GRAYLOG_ENABLED: "True",
            GelfSettings.GRAYLOG_PROTOCOL: "UDP",
            GelfSettings.GRAYLOG_HOST: "127.0.0.2",
            GelfSettings.GRAYLOG_PORT: 12121,
            GelfSettings.GRAYLOG_OPTIONAL_FIELDS: '{"localname": "encab2"}',
        }

        settings.update_default_handler(environment)

        self.assertEqual(2, len(settings.handlers))
        handler = settings.handlers["default"]
        self.assertEqual("UDP", handler.protocol)
        self.assertEqual("127.0.0.2", handler.host)
        self.assertEqual(12121, handler.port)
        self.assertEqual({"localname": "encab2"}, handler.optional_fields)
        self.assertEqual(True, handler.enabled)

    def testOverrideSettingsWithEnvironment(self):
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

        settings = GelfSettings.load(settings_data)

        environment = {
            GelfSettings.GRAYLOG_ENABLED: "True",
            GelfSettings.GRAYLOG_PROTOCOL: "UDP",
            GelfSettings.GRAYLOG_HOST: "127.0.0.2",
            GelfSettings.GRAYLOG_PORT: 12121,
            GelfSettings.GRAYLOG_OPTIONAL_FIELDS: '{"localname": "encab2"}',
        }

        settings.update_default_handler(environment)

        self.assertEqual(1, len(settings.handlers))
        handler = settings.handlers["default"]
        self.assertEqual("UDP", handler.protocol)
        self.assertEqual("127.0.0.2", handler.host)
        self.assertEqual(12121, handler.port)
        self.assertEqual({"localname": "encab2"}, handler.optional_fields)
        self.assertEqual(True, handler.enabled)
