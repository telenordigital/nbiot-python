import os
import requests

class Client:
	"""Construct a new client.  If addr or teken is not provided, the default
	configuration is used.  The default configuration can be specified in a
	configuration file (~/.horde) or through environment variables.  The config
	file is expected to contain a "address=<value>" line and/or a "token=<value>"
	line.  The environment variables are HORDE_ADDRESS and HORDE_TOKEN"""
	def __init__(self, addr=None, token=None):
		if addr is None or token is None:
			addr, token = addressTokenFromConfig(CONFIG_FILE)
		self.addr = addr
		self.token = token

	def request(self, method, path, x=None):
		json = x and x.json()
		headers = {'X-API-Token': self.token, 'Content-Type': 'application/json'}
		resp = requests.request(method, self.addr + path, json=json, headers=headers)
		if not resp.ok:
			raise ClientError(resp)
		if method is not 'DELETE':
			return resp.json()

	def get_teams(self):
		x = self.request('GET', '/teams')
		return map(lambda t: Team(json=t), x['teams'])
	def get_team(self, id):
		x = self.request('GET', '/teams/'+id)
		return Team(json=x)
	def create_team(self, team):
		x = self.request('POST', '/teams', team)
		return Team(json=x)
	def update_team(self, team):
		x = self.request('PATCH', '/teams/'+team.id, team)
		return Team(json=x)
	def delete_team(self, id):
		self.request('DELETE', '/teams/'+id)

	def get_collections(self):
		x = self.request('GET', '/collections')
		return map(lambda c: Collection(json=c), x['collections'])
	def get_collection(self, id):
		x = self.request('GET', '/collections/'+id)
		return Collection(json=x)
	def create_collection(self, collection):
		x = self.request('POST', '/collections', collection)
		return Collection(json=x)
	def update_collection(self, collection):
		x = self.request('PATCH', '/collections/'+collection.id, collection)
		return Collection(json=x)
	def delete_collection(self, id):
		self.request('DELETE', '/collections/'+id)

	def get_devices(self, collection_id):
		x = self.request('GET', '/collections/{0}/devices'.format(collection_id))
		return map(lambda d: Device(json=d), x['devices'])
	def get_device(self, collection_id, device_id):
		x = self.request('GET', '/collections/{0}/devices/{1}'.format(collection_id, device_id))
		return Device(json=x)
	def create_device(self, collection_id, device):
		x = self.request('POST', '/collections/{0}/devices'.format(collection_id), device)
		return Device(json=x)
	def update_device(self, collection_id, device):
		x = self.request('PATCH', '/collections/{0}/devices/{1}'.format(collection_id, device.id), device)
		return Device(json=x)
	def delete_device(self, collection_id, device_id):
		self.request('DELETE', '/collections/{0}/devices/{1}'.format(collection_id, device_id))


class ClientError(Exception):
	def __init__(self, resp):
		self.http_status_code = resp.status_code
		self.message = resp.text

	def __str__(self):
		return self.message


CONFIG_FILE = '.horde'
DEFAULT_ADDRESS = 'https://api.nbiot.telenor.io'
ADDRESS_ENV_VAR = 'HORED_ADDRESS'
TOKEN_ENV_VAR = 'HORED_TOKEN'

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
			self.members = map(lambda m: Member(m), json.get('members', []))
			self.tags = json.get('tags', {})
			return
		self.id = id
		self.members = members or []
		self.tags = tags or {}

	def json(self):
		return {
			'teamId': self.id,
			'members': map(lambda m: m.json(), self.members),
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
