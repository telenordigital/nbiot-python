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

	team = client.create_team(Team())
	try:
		teams = client.get_teams()
		assert contains(teams, team)

		key = 'test_key'
		value = 'test_value'
		team.tags[key] = value
		team = client.update_team(team)
		assert team.tags[key] == value
	finally:
		client.delete_team(team.id)
		teams = client.get_teams()
		assert not contains(teams, team)

def test_collections():
	client = Client()

	collection = client.create_collection(Collection())
	try:
		collections = client.get_collections()
		assert contains(collections, collection)

		key = 'test_key'
		value = 'test_value'
		collection.tags[key] = value
		collection = client.update_collection(collection)
		assert collection.tags[key] == value
	finally:
		client.delete_collection(collection.id)
		collections = client.get_collections()
		assert not contains(collections, collection)

def test_devices():
	client = Client()
	collection = client.create_collection(Collection())

	try:
		devices = client.get_devices(collection.id)
		assert len(devices) == 0

		device = client.create_device(collection.id, Device(imsi='12', imei='34'))
		try:
			devices = client.get_devices(collection.id)
			assert len(devices) == 1

			key = 'test_key'
			value = 'test_value'
			device.tags[key] = value
			device = client.update_device(collection.id, device)
			assert device.tags[key] == value
		finally:
			client.delete_device(collection.id, device.id)
			devices = client.get_devices(collection.id)
			assert len(devices) == 0
	finally:
		client.delete_collection(collection.id)

def test_outputs():
	client = Client()
	collection = client.create_collection(Collection())

	try:
		output = client.create_output(collection.id, IFTTTOutput(key='abc', event_name='def'))
		try:
			outputs = client.get_outputs(collection.id)
			assert contains(outputs, output)

			value = 'ghi'
			output.key = value
			output = client.update_output(collection.id, output)
			assert output.key == value
		finally:
			client.delete_output(collection.id, output.id)
			outputs = client.get_outputs(collection.id)
			assert not contains(outputs, output)
	finally:
		client.delete_collection(collection.id)

@pytest.mark.asyncio
async def test_output_stream():
	client = Client()
	collection = client.create_collection(Collection())
	try:
		stream = await client.collection_output_stream(collection.id)
		deadline = asyncio.create_task(asyncio.sleep(4))
		while True:
			msg_task = asyncio.create_task(stream.recv())
			done, _ = await asyncio.wait({msg_task, deadline}, return_when=asyncio.FIRST_COMPLETED)
			if deadline in done:
				break
			msg = msg_task.result()
			print(msg.payload)

		await stream.close()
	finally:
		client.delete_collection(collection.id)

def contains(X, x):
	return any([y.id == x.id for y in X])