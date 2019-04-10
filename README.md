# nbiot-python
[![Travis-CI](https://api.travis-ci.com/telenordigital/nbiot-python.svg)](https://travis-ci.com/telenordigital/nbiot-python)

NBIoT-Python provides a Python client for the REST API for Telenor NB-IoT.

## Configuration

The configuration file is located at `${HOME}/.telenor-nbiot`. The file is a simple
list of key/value pairs. Additional values are ignored. Comments must start
with a `#`:

    #
    # This is the URL of the Telenor NB-IoT REST API. The default value is
    # https://api.nbiot.telenor.io and can usually be omitted.
    address=https://api.nbiot.telenor.io

    #
    # This is the API token. Create new token by logging in to the Telenor NB-IoT
    # front-end at https://nbiot.engineering and create a new token there.
    token=<your api token goes here>


The configuration file settings can be overridden by setting the environment
variables `TELENOR_NBIOT_ADDRESS` and `TELENOR_NBIOT_TOKEN`. If you only use environment variables
the configuration file can be ignored.  Finally, there is a Client constructor that
accepts the address and token directly.

## Updating resources

The various `Client.update*` methods work via HTTP PATCH, which means they will only modify or set fields, not delete them.  There are special `Client.delete*tag` methods for deleting tags.

# Sample code

```python
from nbiot import nbiot

client = nbiot.Client()
stream = await client.collection_output_stream('<YOUR_COLLECTION_ID>')
while True:
	try:
		msg = await stream.recv()
	except nbiot.OutputStreamClosed:
		break
	print(msg.payload)
```

# Development

Development is done using [Pipenv](https://docs.pipenv.org/).  Run `pipenv sync --dev` to install all dependencies.

Because Python has not properly solved dependency management yet, dependencies must be be repeated in [setup.py](setup.py) under the `install_requires` entry.

## Testing

Tests are written using [pytest](https://pytest.org/).  Run `pipenv run pytest` to run all the tests.

## Deployment

To build and upload a new version to PyPI, make sure that you are using Python 3 and run

```bash
python setup.py sdist
python setup.py bdist_wheel
twine upload dist/*          # `pip install twine` to get this tool
```
