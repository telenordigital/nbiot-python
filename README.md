# horde-python
Horde-Python provides a Python client for the REST API for Telenor NB-IoT.

## Configuration

The configuration file is located at `${HOME}/.horde`. The file is a simple
list of key/value pairs. Additional values are ignored. Comments must start
with a `#`:

    #
    # This is the URL of the Horde REST API. The default value is
    # https://api.nbiot.telenor.io and can usually be omitted.
    address=https://api.nbiot.telenor.io

    #
    # This is the API token. Create new token by logging in to the Horde
    # front-end at https://nbiot.engineering and create a new token there.
    token=<your api token goes here>


The configuration file settings can be overridden by setting the environment
variables `HORDE_ADDRESS` and `HORDE_TOKEN`. If you only use environment variables
the configuration file can be ignored.  Finally, there is a Client constructor that
accepts the address and token directly.

# Development

Development is done using [Pipenv](https://docs.pipenv.org/).  Run `pipenv install --dev` to install all dependencies.

## Testing

Tests are written using [pytest](https://pytest.org/).  Run `pipenv run pytest` to run all the tests.