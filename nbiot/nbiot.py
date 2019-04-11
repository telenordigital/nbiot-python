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

	def system_defaults(self):
		x = self._request('GET', '/system')
		return SystemDefaults(x)

	def teams(self):
		x = self._request('GET', '/teams')
		return [Team(json=t) for t in x['teams']]
	def team(self, id):
		x = self._request('GET', '/teams/'+id)
		return Team(json=x)
	def create_team(self, team):
		x = self._request('POST', '/teams', team)
		return Team(json=x)
	def update_team(self, team):
		x = self._request('PATCH', '/teams/'+team.id, team)
		return Team(json=x)
	def update_team_member_role(self, team_id, user_id, role):
		x = self._request('PATCH', '/teams/{0}/members/{1}'.format(team_id, user_id), Member(role=role))
		return Member(json=x)
	def delete_team_member(self, team_id, user_id):
		self._request('DELETE', '/teams/{0}/members/{1}'.format(team_id, user_id))
	def delete_team_tag(self, id, name):
		self._request('DELETE', '/teams/{0}/tags/{1}'.format(id, name))
	def delete_team(self, id):
		self._request('DELETE', '/teams/'+id)


	def invites(self, team_id):
		x = self._request('GET', '/teams/{0}/invites'.format(team_id))
		return [Invite(json=i) for i in x['invites']]
	def invite(self, team_id, code):
		x = self._request('GET', '/teams/{0}/invites/{1}'.format(team_id, code))
		return Invite(json=x)
	def create_invite(self, team_id):
		x = self._request('POST', '/teams/{0}/invites'.format(team_id))
		return Invite(json=x)
	def accept_invite(self, code):
		x = self._request('POST', '/teams/accept', Invite(code=code))
		return Team(json=x)
	def delete_invite(self, team_id, code):
		self._request('DELETE', '/teams/{0}/invites/{1}'.format(team_id, code))


	def collections(self):
		x = self._request('GET', '/collections')
		return [Collection(json=c) for c in x['collections']]
	def collection(self, id):
		x = self._request('GET', '/collections/'+id)
		return Collection(json=x)
	def create_collection(self, collection):
		x = self._request('POST', '/collections', collection)
		return Collection(json=x)
	def update_collection(self, collection):
		x = self._request('PATCH', '/collections/'+collection.id, collection)
		return Collection(json=x)
	def delete_collection_tag(self, id, name):
		self._request('DELETE', '/collections/{0}/tags/{1}'.format(id, name))
	def delete_collection(self, id):
		self._request('DELETE', '/collections/'+id)

	def devices(self, collection_id):
		x = self._request('GET', '/collections/{0}/devices'.format(collection_id))
		return [Device(json=d) for d in x['devices']]
	def device(self, collection_id, device_id):
		x = self._request('GET', '/collections/{0}/devices/{1}'.format(collection_id, device_id))
		return Device(json=x)
	def create_device(self, collection_id, device):
		x = self._request('POST', '/collections/{0}/devices'.format(collection_id), device)
		return Device(json=x)
	def update_device(self, collection_id, device):
		x = self._request('PATCH', '/collections/{0}/devices/{1}'.format(collection_id, device.id), device)
		return Device(json=x)
	def delete_device_tag(self, collection_id, device_id, name):
		self._request('DELETE', '/collections/{0}/devices/{1}/tags/{2}'.format(collection_id, device_id, name))
	def delete_device(self, collection_id, device_id):
		self._request('DELETE', '/collections/{0}/devices/{1}'.format(collection_id, device_id))

	def outputs(self, collection_id):
		x = self._request('GET', '/collections/{0}/outputs'.format(collection_id))
		return [_output(o) for o in x['outputs']]
	def output(self, collection_id, output_id):
		x = self._request('GET', '/collections/{0}/outputs/{1}'.format(collection_id, output_id))
		return _output(x)
	def create_output(self, collection_id, output):
		x = self._request('POST', '/collections/{0}/outputs'.format(collection_id), output)
		return _output(x)
	def update_output(self, collection_id, output):
		x = self._request('PATCH', '/collections/{0}/outputs/{1}'.format(collection_id, output.id), output)
		return _output(x)
	def output_logs(self, collection_id, output_id):
		x = self._request('GET', '/collections/{0}/outputs/{1}/logs'.format(collection_id, output_id))
		return [OutputLogEntry(l) for l in x['logs']]
	def output_status(self, collection_id, output_id):
		x = self._request('GET', '/collections/{0}/outputs/{1}/status'.format(collection_id, output_id))
		return OutputStatus(x)
	def delete_output_tag(self, collection_id, output_id, name):
		self._request('DELETE', '/collections/{0}/outputs/{1}/tags/{2}'.format(collection_id, output_id, name))
	def delete_output(self, collection_id, output_id):
		self._request('DELETE', '/collections/{0}/outputs/{1}'.format(collection_id, output_id))

	def collection_data(self, collection_id, since=None, until=None, limit=0):
		return self._data('/collections/{0}'.format(collection_id))
	def device_data(self, collection_id, device_id, since=None, until=None, limit=0):
		return self._data('/collections/{0}/devices/{1}'.format(collection_id, device_id))
	def _data(self, path, since=None, until=None, limit=0):
		since = 0 if since is None else int(since.timestamp() * 1000)
		until = 0 if until is None else int(until.timestamp() * 1000)
		x = self._request('GET', '{0}/data?since={1}&until={2}&limit={3}'.format(path, since, until, limit))
		return [OutputDataMessage(m) for m in x['messages']]

	def send(self, collection_id, device_id, msg):
		self._request('POST', '/collections/{0}/devices/{1}/to'.format(collection_id, device_id), msg)
	def broadcast(self, collection_id, msg):
		x = self._request('POST', '/collections/{0}/to'.format(collection_id), msg)
		return BroadcastResult(x)

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

	try:
		with open(filepath) as f:
			lines = f.readlines()
	except FileNotFoundError:
		return address, token
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


class SystemDefaults:
	def __init__(self, json):
		self.default_field_mask = FieldMask(json['defaultFieldMask'])
		self.forced_field_mask = FieldMask(json['forcedFieldMask'])

class FieldMask:
	def __init__(self, imsi=None, imei=None, location=None, msisdn=None, json=None):
		if json is not None:
			self.imsi = json['imsi']
			self.imei = json['imei']
			self.location = json['location']
			self.msisdn = json['msisdn']
			return
		self.imsi = imsi
		self.imei = imei
		self.location = location
		self.msisdn = msisdn

	def json(self):
		return {
			'imsi': self.imsi,
			'imei': self.imei,
			'location': self.location,
			'msisdn': self.msisdn,
		}

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
	def __init__(
		self,
		user_id=None,
		role=None,
		name=None,
		email=None,
		phone=None,
		verifiedEmail=None,
		verifiedPhone=None,
		connectId=None,
		gitHubLogin=None,
		authType=None,
		avatarUrl=None,
		json=None,
	):
		if json is not None:
			self.user_id = json['userId']
			self.role = json['role']
			self.name = json['name']
			self.email = json['email']
			self.phone = json['phone']
			self.verifiedEmail = json['verifiedEmail']
			self.verifiedPhone = json['verifiedPhone']
			self.connectId = json['connectId']
			self.gitHubLogin = json['gitHubLogin']
			self.authType = json['authType']
			self.avatarUrl = json['avatarUrl']
			return
		self.user_id = user_id
		self.role = role
		self.name = name
		self.email = email
		self.phone = phone
		self.verifiedEmail = verifiedEmail
		self.verifiedPhone = verifiedPhone
		self.connectId = connectId
		self.gitHubLogin = gitHubLogin
		self.authType = authType
		self.avatarUrl = avatarUrl

	def json(self):
		return {
			'user_id': self.user_id,
			'role': self.role,
			'user_id': self.user_id,
			'role': self.role,
			'name': self.name,
			'email': self.email,
			'phone': self.phone,
			'verifiedEmail': self.verifiedEmail,
			'verifiedPhone': self.verifiedPhone,
			'connectId': self.connectId,
			'gitHubLogin': self.gitHubLogin,
			'authType': self.authType,
			'avatarUrl': self.avatarUrl,
		}


class Invite:
	def __init__(self, code=None, created_at=None, json=None):
		if json is not None:
			self.code = json['code']
			self.created_at = json['createdAt']
			return
		self.code = code
		self.created_at = created_at

	def json(self):
		return {
			'code': self.code,
			'createdAt': self.created_at,
		}


class Collection:
	def __init__(self, id=None, team_id=None, field_mask=None, tags=None, json=None):
		if json is not None:
			self.id = json['collectionId']
			self.team_id = json['teamId']
			self.field_mask = json['fieldMask']
			self.tags = json.get('tags', {})
			return
		self.id = id
		self.team_id = team_id
		self.field_mask = field_mask
		self.tags = tags or {}

	def json(self):
		return {
			'collectionId': self.id,
			'teamId': self.team_id,
			'fieldMask': self.field_mask,
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
		'udp': UDPOutput,
	}[json['type']](json=json)

class WebHookOutput:
	def __init__(self, id=None, collection_id=None, url=None, basic_auth_user=None, basic_auth_pass=None, custom_header_name=None, custom_header_value=None, enabled=None, tags=None, json=None):
		if json is not None:
			cfg = json['config']
			self.id = json['outputId']
			self.collection_id = json['collectionId']
			self.url = cfg['url']
			self.basic_auth_user = cfg.get('basicAuthUser')
			self.basic_auth_pass = cfg.get('basicAuthPass')
			self.custom_header_name = cfg.get('customHeaderName')
			self.custom_header_value = cfg.get('customHeaderValue')
			self.enabled = json['enabled']
			self.tags = json.get('tags', {})
			return
		self.id = id
		self.collection_id = collection_id
		self.url = url
		self.basic_auth_user = basic_auth_user
		self.basic_auth_pass = basic_auth_pass
		self.custom_header_name = custom_header_name
		self.custom_header_value = custom_header_value
		self.enabled = enabled
		self.tags = tags or {}

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
			'enabled': self.enabled,
			'tags': self.tags,
		}

class MQTTOutput:
	def __init__(self, id=None, collection_id=None, endpoint=None, disable_cert_check=None, username=None, password=None, client_id=None, topic_name=None, enabled=None, tags=None, json=None):
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
			self.enabled = json['enabled']
			self.tags = json.get('tags', {})
			return
		self.id = id
		self.collection_id = collection_id
		self.endpoint = endpoint
		self.disable_cert_check = disable_cert_check
		self.username = username
		self.password = password
		self.client_id = client_id
		self.topic_name = topic_name
		self.enabled = enabled
		self.tags = tags or {}

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
			'enabled': self.enabled,
			'tags': self.tags,
		}

class IFTTTOutput:
	def __init__(self, id=None, collection_id=None, key=None, event_name=None, as_is_payload=None, enabled=None, tags=None, json=None):
		if json is not None:
			cfg = json['config']
			self.id = json['outputId']
			self.collection_id = json['collectionId']
			self.key = cfg['key']
			self.event_name = cfg['eventName']
			self.as_is_payload = cfg.get('asIsPayload', False)
			self.enabled = json['enabled']
			self.tags = json.get('tags', {})
			return
		self.id = id
		self.collection_id = collection_id
		self.key = key
		self.event_name = event_name
		self.as_is_payload = as_is_payload
		self.enabled = enabled
		self.tags = tags or {}

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
			'enabled': self.enabled,
			'tags': self.tags,
		}

class UDPOutput:
	def __init__(self, id=None, collection_id=None, host=None, port=None, enabled=None, tags=None, json=None):
		if json is not None:
			cfg = json['config']
			self.id = json['outputId']
			self.collection_id = json['collectionId']
			self.host = cfg['host']
			self.port = cfg['port']
			self.enabled = json['enabled']
			self.tags = json.get('tags', {})
			return
		self.id = id
		self.collection_id = collection_id
		self.host = host
		self.port = port
		self.enabled = enabled
		self.tags = tags or {}

	def json(self):
		return {
			'outputId': self.id,
			'collectionId': self.collection_id,
			'type': 'ifttt',
			'config': {
				'host': self.host,
				'port': self.port,
			},
			'enabled': self.enabled,
			'tags': self.tags,
		}

class OutputLogEntry:
	def __init__(self, json):
		self.message = json['message']
		self.timestamp = datetime.utcfromtimestamp(json['timestamp']/1000)
		self.repeated = json['repeated']

class OutputStatus:
	def __init__(self, json):
		self.error_count = json['errorCount']
		self.forwarded = json['forwarded']
		self.received = json['received']
		self.retries = json['retries']


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

class DownstreamMessage:
	def __init__(self, port, payload):
		if not isinstance(payload, bytes):
			raise TypeError('payload must be bytes')
		self.port = port
		self.payload = payload

	def json(self):
		return {
			'port': self.port,
			'payload': base64.b64encode(self.payload).decode('ascii'),
		}

class BroadcastResult:
	def __init__(self, json):
		self.sent = json['sent']
		self.failed = json['failed']
		self.errors = [BroadcastError(e) for e in json['errors']]

class BroadcastError:
	def __init__(self, json):
		self.device_id = json['deviceId']
		self.message = json['message']
