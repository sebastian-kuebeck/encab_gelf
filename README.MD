# GELF Plugin for Encab

Redirects [encab](https://pypi.org/project/encab/) logging to Graylog using the GELF protocol.

## Installation

```shell
pip install encab encab_gelf
```

## Configuration

See [encab documentation](https://encab.readthedocs.io/en/latest/index.html) for an introduction to encab and encab configuration.

### Example GELF Extension configuration

```yaml
extensions:
    encab_gelf:
        module: encab_gelf
        enabled: true
        settings:
            handlers:
                default:
                    protocol: HTTP
                    host: localhost
                    port: 11201
                    optional_fields:
                        localname: encab
```

### Properties

- `protocol`: String, One of `HTTP`, `HTTPS`, `UDP`, `TCP`, `TLS`
    the GELF Protocol of the associated Graylog input
- `host`: String
    Graylog input host or IP address
- `port`: Integer, default=12201
    Graylog port
- `optional_fields`: Map
    optional fields added to every log record


### Protocol specific properties

#### HTTP

- `path`: String, default="/gelf"
    path of the HTTP input
- `compress`: Boolean, default=True
    if true, compress log messages before sending them to the server
- `timeout`: Float, default=5.0
    amount of seconds that HTTP client should wait before it discards the request if the server doesn't respond

#### UDP

- `chunk_size`: Integer, default=1300
    maximum length of the message. If log length exceeds this value, it splits into multiple chunks.

#### HTTPS

- `validate`: Boolean, default=False
    if true, validate server certificate. In that case ca_certs are required
- `ca_certs`: String
    path to CA bundle file. For instance, on CentOS it would be '/etc/pki/tls/certs/ca-bundle.crt'

#### TLS

- `certfile`: String
    path to the certificate file that is used to identify ourselves to the server
- `keyfile`: String
    path to the private key. If the private key is stored with the certificate, this parameter can be ignored.

### Environment variables

- `GRAYLOG_ENABLED`: 
    `True`, `true` or `1` overrides `enabled` setting
    in configuration file
- `GRAYLOG_PROTOCOL`: one of `HTTP`, `HTTPS`, `UDP`, `TCP`, `TLS`
    overrides the protocol for the handler `default`.
- `GRAYLOG_HOST`:
    overridesthe the host name or ip address for the handler `default` of the associated Graylog Input.
- `GRAYLOG_PORT`:
    overrides the port for the handler `default` of the associated Graylog Input.
- `GRAYLOG_OPTIONAL_FIELDS`:
    overrides optional fields for the handler `default`. The value mujst be a JSON encoded object.
    
    Example: `{"localname": "encab"}`


## Further information

- [encab](https://pypi.org/project/encab/)
- [Graylog](https://github.com/Graylog2/graylog2-server)
- [pygelf](https://pypi.org/project/pygelf/)
