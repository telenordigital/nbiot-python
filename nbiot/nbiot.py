import asyncio
import base64
from datetime import datetime
import json
import os

import requests
from urllib.parse import urlparse
import websockets

class Client:
	"""Construct a new client.  If addr or teken is not provided, the default
	configuration is used.  The default configuration can be specified in a
	configuration file (~/.telenor-nbiot) or through environment variables.  The config
	file is expected to contain a "address=<value>" line and/or a "token=<value>"
	line.  The environment variables are TELENOR_NBIOT_ADDRESS and TELENOR_NBIOT_TOKEN"""
	def __init__(self, addr=None, token=None):
		if addr is None or token is None:
			addr, token = addressTokenFromConfig(CONFIG_FILE)
		self.addr = addr
		self.token = token
		self.ping()

	def ping(self):
		try:
			self._request('GET', '/')
		except ClientError as err:
			# A token with restricted access will receive 403 Forbidden from "/"
			# but that still indicates a succesful connection.
			if err.http_status_code != requests.codes.forbidden:
				raise err

	def get_teams(self):
		x = self._request('GET', '/teams')
		return [Team(json=t) for t in x['teams']]
	def get_team(self, id):
		x = self._request('GET', '/teams/'+id)
		return Team(json=x)
	def create_team(self, team):
		x = self._request('POST', '/teams', team)
		return Team(json=x)
	def update_team(self, team):
		x = self._request('PATCH', '/teams/'+team.id, team)
		return Team(json=x)
	def delete_team(self, id):
		self._request('DELETE', '/teams/'+id)

	def get_collections(self):
		x = self._request('GET', '/collections')
		return [Collection(json=c) for c in x['collections']]
	def get_collection(self, id):
		x = self._request('GET', '/collections/'+id)
		return Collection(json=x)
	def create_collection(self, collection):
		x = self._request('POST', '/collections', collection)
		return Collection(json=x)
	def update_collection(self, collection):
		x = self._request('PATCH', '/collections/'+collection.id, collection)
		return Collection(json=x)
	def delete_collection(self, id):
		self._request('DELETE', '/collections/'+id)

	def get_devices(self, collection_id):
		x = self._request('GET', '/collections/{0}/devices'.format(collection_id))
		return [Device(json=d) for d in x['devices']]
	def get_device(self, collection_id, device_id):
		x = self._request('GET', '/collections/{0}/devices/{1}'.format(collection_id, device_id))
		return Device(json=x)
	def create_device(self, collection_id, device):
		x = self._request('POST', '/collections/{0}/devices'.format(collection_id), device)
		return Device(json=x)
	def update_device(self, collection_id, device):
		x = self._request('PATCH', '/collections/{0}/devices/{1}'.format(collection_id, device.id), device)
		return Device(json=x)
	def delete_device(self, collection_id, device_id):
		self._request('DELETE', '/collections/{0}/devices/{1}'.format(collection_id, device_id))

	def get_outputs(self, collection_id):
		x = self._request('GET', '/collections/{0}/outputs'.format(collection_id))
		return [_output(o) for o in x['outputs']]
	def get_output(self, collection_id, output_id):
		x = self._request('GET', '/collections/{0}/outputs/{1}'.format(collection_id, output_id))
		return _output(x)
	def create_output(self, collection_id, output):
		x = self._request('POST', '/collections/{0}/outputs'.format(collection_id), output)
		return _output(x)
	def update_output(self, collection_id, output):
		x = self._request('PATCH', '/collections/{0}/outputs/{1}'.format(collection_id, output.id), output)
		return _output(x)
	def delete_output(self, collection_id, output_id):
		self._request('DELETE', '/collections/{0}/outputs/{1}'.format(collection_id, output_id))

	def _request(self, method, path, x=None):
		json = x and x.json()
		headers = {'X-API-Token': self.token, 'Content-Type': 'application/json'}
		resp = requests.request(method, self.addr + path, json=json, headers=headers)
		if not resp.ok:
			raise ClientError(resp)
		if method is not 'DELETE':
			return resp.json()

	def collection_output_stream(self, id):
		return self._output_stream('/collections/'+id)
	def device_output_stream(self, collection_id, device_id):
		return self._output_stream('/collections/{0}/devices/{1}'.format(collection_id, device_id))

	async def _output_stream(self, path):
		url = urlparse(self.addr)
		scheme = 'wss'
		ssl = True
		if url.scheme == 'http':
			scheme = 'ws'
			ssl = False
		hostport = url.hostname
		if url.port is not None:
			hostport += ":" + url.port
		ws = await websockets.connect(
			'{0}://{1}{2}/from'.format(scheme, hostport, path),
			ssl=ssl,
			extra_headers=[('X-API-Token', self.token)],
			origin='http://www.example.com',
		)
		return OutputStream(ws)


class ClientError(Exception):
	def __init__(self, resp):
		self.http_status_code = resp.status_code
		self.message = resp.text

	def __str__(self):
		return self.message


CONFIG_FILE = '.telenor-nbiot'
DEFAULT_ADDRESS = 'https://api.nbiot.telenor.io'
ADDRESS_ENV_VAR = 'TELENOR_NBIOT_ADDRESS'
TOKEN_ENV_VAR = 'TELENOR_NBIOT_TOKEN'

def addressTokenFromConfig(filename):
	address, token = readConfig(getFullPath(filename))

	address = os.getenv(ADDRESS_ENV_VAR, address)
	token = os.getenv(TOKEN_ENV_VAR, token)

	return address, token

def getFullPath(filename):
	home = os.path.expanduser("~")
	return os.path.join(home, filename)

def readConfig(filepath):
	address = DEFAULT_ADDRESS
	token = ''

	with open(filepath) as f:
		lines = f.readlines()
	lines = [line.strip() for line in lines]
	lineno = 0
	for line in lines:
		lineno += 1
		if len(line) == 0 or line[0] == '#':
			# ignore comments and empty lines
			continue
		words = line.split('=', 1)
		if len(words) != 2:
			raise Exception('Not a key value expression on line {0} in {1}: {2}'.format(lineno, filepath, line))
		if words[0] == 'address':
			address = words[1]
		elif words[0] == 'token':
			token = words[1]
		else:
			raise Exception('Unknown keyword on line {0} in {1}: {2}'.format(lineno, filepath, line))
	return address, token


class Team:
	def __init__(self, id=None, members=None, tags=None, json=None):
		if json is not None:
			self.id = json['teamId']
			self.members = [Member(m) for m in json.get('members', [])]
			self.tags = json.get('tags', {})
			return
		self.id = id
		self.members = members or []
		self.tags = tags or {}

	def json(self):
		return {
			'teamId': self.id,
			'members': [m.json() for m in self.members],
			'tags': self.tags,
		}


class Member:
	def __init__(self, user_id=None, role=None, json=None):
		if json is not None:
			self.user_id = json['userId']
			self.role = json['role']
			return
		self.user_id = user_id
		self.role = role

	def json(self):
		return {
			'user_id': self.user_id,
			'role': self.role,
		}


class Collection:
	def __init__(self, id=None, team_id=None, tags=None, json=None):
		if json is not None:
			self.id = json['collectionId']
			self.team_id = json['teamId']
			self.tags = json.get('tags', {})
			return
		self.id = id
		self.team_id = team_id
		self.tags = tags or {}

	def json(self):
		return {
			'collectionId': self.id,
			'teamId': self.team_id,
			'tags': self.tags,
		}


class Device:
	def __init__(self, id=None, collection_id=None, imsi=None, imei=None, tags=None, json=None):
		if json is not None:
			self.id = json['deviceId']
			self.collection_id = json['collectionId']
			self.imsi = json['imsi']
			self.imei = json['imei']
			self.tags = json.get('tags', {})
			return
		self.id = id
		self.collection_id = collection_id
		self.imsi = imsi
		self.imei = imei
		self.tags = tags or {}

	def json(self):
		return {
			'deviceId': self.id,
			'collectionId': self.collection_id,
			'imsi': self.imsi,
			'imei': self.imei,
			'tags': self.tags,
		}


def _output(json):
	return {
		'webhook': WebHookOutput,
		'mqtt': MQTTOutput,
		'ifttt': IFTTTOutput,
	}[json['type']](json=json)

class WebHookOutput:
	def __init__(self, id=None, collection_id=None, url=None, basic_auth_user=None, basic_auth_pass=None, custom_header_name=None, custom_header_value=None, json=None):
		if json is not None:
			cfg = json['config']
			self.id = json['outputId']
			self.collection_id = json['collectionId']
			self.url = cfg['url']
			self.basic_auth_user = cfg.get('basicAuthUser')
			self.basic_auth_pass = cfg.get('basicAuthPass')
			self.custom_header_name = cfg.get('customHeaderName')
			self.custom_header_value = cfg.get('customHeaderValue')
			return
		self.id = id
		self.collection_id = collection_id
		self.url = url
		self.basic_auth_user = basic_auth_user
		self.basic_auth_pass = basic_auth_pass
		self.custom_header_name = custom_header_name
		self.custom_header_value = custom_header_value

	def json(self):
		return {
			'outputId': self.id,
			'collectionId': self.collection_id,
			'type': 'webhook',
			'config': {
				'url': self.url,
				'basicAuthUser': self.basic_auth_user,
				'basicAuthPass': self.basic_auth_pass,
				'customHeaderName': self.custom_header_name,
				'customHeaderValue': self.custom_header_value,
			},
		}

class MQTTOutput:
	def __init__(self, id=None, collection_id=None, endpoint=None, disable_cert_check=None, username=None, password=None, client_id=None, topic_name=None, json=None):
		if json is not None:
			cfg = json['config']
			self.id = json['outputId']
			self.collection_id = json['collectionId']
			self.endpoint = cfg['endpoint']
			self.disable_cert_check = cfg.get('disableCertCheck')
			self.username = cfg.get('username')
			self.password = cfg.get('password')
			self.client_id = cfg['clientId']
			self.topic_name = cfg['topicName']
			return
		self.id = id
		self.collection_id = collection_id
		self.endpoint = endpoint
		self.disable_cert_check = disable_cert_check
		self.username = username
		self.password = password
		self.client_id = client_id
		self.topic_name = topic_name

	def json(self):
		return {
			'outputId': self.id,
			'collectionId': self.collection_id,
			'type': 'mqtt',
			'config': {
				'endpoint': self.endpoint,
				'disableCertCheck': self.disable_cert_check,
				'username': self.username,
				'password': self.password,
				'clientId': self.client_id,
				'topicName': self.topic_name,
			},
		}

class IFTTTOutput:
	def __init__(self, id=None, collection_id=None, key=None, event_name=None, as_is_payload=None, json=None):
		if json is not None:
			cfg = json['config']
			self.id = json['outputId']
			self.collection_id = json['collectionId']
			self.key = cfg['key']
			self.event_name = cfg['eventName']
			self.as_is_payload = cfg.get('asIsPayload', False)
			return
		self.id = id
		self.collection_id = collection_id
		self.key = key
		self.event_name = event_name
		self.as_is_payload = as_is_payload

	def json(self):
		return {
			'outputId': self.id,
			'collectionId': self.collection_id,
			'type': 'ifttt',
			'config': {
				'key': self.key,
				'eventName': self.event_name,
				'asIsPayload': self.as_is_payload,
			},
		}


class OutputStream:
	def __init__(self, ws):
		self.ws = ws

	async def recv(self):
		try:
			while True:
				msg = json.loads(await self.ws.recv())
				if msg['type'] == 'data':
					return OutputDataMessage(json=msg)
		except websockets.exceptions.ConnectionClosed:
			raise OutputStreamClosed()

	async def close(self):
		await self.ws.close()

class OutputStreamClosed(Exception):
	pass


class OutputDataMessage:
	def __init__(self, json):
		self.device = Device(json=json['device'])
		self.payload = base64.b64decode(json['payload'])
		self.received = datetime.utcfromtimestamp(json['received']/1000)
