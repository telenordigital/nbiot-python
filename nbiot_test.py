import asyncio
import pytest

from nbiot import *

def test_config():
	addr, token = addressTokenFromConfig(CONFIG_FILE)
	assert type(addr) is str
	assert type(token) is str

def test_client():
	Client()

def test_teams():
	client = Client()
	teams = client.get_teams()
	assert len(teams) == 1

	team = client.get_team(teams[0].id)
	assert len(team.members) == 1

	team = client.create_team(Team())
	teams = client.get_teams()
	assert len(teams) == 2

	key = 'test_key'
	value = 'test_value'
	team.tags[key] = value
	team = client.update_team(team)
	assert team.tags[key] == value

	client.delete_team(team.id)
	teams = client.get_teams()
	assert len(teams) == 1

def test_collections():
	client = Client()
	collections = client.get_collections()
	assert len(collections) == 1

	collection = client.create_collection(Collection())
	collections = client.get_collections()
	assert len(collections) == 2

	key = 'test_key'
	value = 'test_value'
	collection.tags[key] = value
	collection = client.update_collection(collection)
	assert collection.tags[key] == value

	client.delete_collection(collection.id)
	collections = client.get_collections()
	assert len(collections) == 1

def test_devices():
	client = Client()
	collection = client.create_collection(Collection())

	devices = client.get_devices(collection.id)
	assert len(devices) == 0

	device = client.create_device(collection.id, Device(imsi='12', imei='34'))
	devices = client.get_devices(collection.id)
	assert len(devices) == 1

	key = 'test_key'
	value = 'test_value'
	device.tags[key] = value
	device = client.update_device(collection.id, device)
	assert device.tags[key] == value

	client.delete_device(collection.id, device.id)
	devices = client.get_devices(collection.id)
	assert len(devices) == 0

	client.delete_collection(collection.id)

@pytest.mark.asyncio
async def test_output():
	client = Client()
	collection = client.create_collection(Collection())

	task = asyncio.create_task(client.collection_output(collection.id, lambda msg: print(msg)))
	await asyncio.sleep(4)
	task.cancel()
	await task

	client.delete_collection(collection.id)
