import asyncio
import random
import requests
import os
import pytest

from nbiot import nbiot

def test_config():
	addr, token = nbiot.addressTokenFromConfig(nbiot.CONFIG_FILE)
	assert type(addr) is str
	assert type(token) is str

def test_client():
	nbiot.Client()

def test_system_defaults():
	nbiot.Client().system_defaults()

def test_teams():
	client = nbiot.Client()

	team = client.create_team(nbiot.Team())
	try:
		teams = client.teams()
		assert contains(teams, team)

		key = 'test_key'
		value = 'test_value'
		team.tags[key] = value
		team = client.update_team(team)
		assert team.tags[key] == value

		assert len(client.invites(team.id)) == 0
		iv = client.create_invite(team.id)
		try:
			ivs = client.invites(team.id)
			assert len(ivs) == 1 and ivs[0].json() == iv.json()
			with pytest.raises(nbiot.ClientError) as err:
				client.accept_invite(iv.code)
			assert err.value.http_status_code == requests.codes.conflict
		finally:
			client.delete_invite(team.id, iv.code)
	finally:
		client.delete_team(team.id)
		teams = client.teams()
		assert not contains(teams, team)

def test_collections():
	client = nbiot.Client()

	collection = client.create_collection(nbiot.Collection())
	try:
		collections = client.collections()
		assert contains(collections, collection)

		key = 'test_key'
		value = 'test_value'
		collection.tags[key] = value
		collection = client.update_collection(collection)
		assert collection.tags[key] == value

		assert len(client.collection_data(collection.id)) == 0
	finally:
		client.delete_collection(collection.id)
		collections = client.collections()
		assert not contains(collections, collection)

def test_devices():
	client = nbiot.Client()
	collection = client.create_collection(nbiot.Collection())

	try:
		devices = client.devices(collection.id)
		assert len(devices) == 0

		device = client.create_device(collection.id, nbiot.Device(imsi='12', imei='34'))
		try:
			devices = client.devices(collection.id)
			assert len(devices) == 1

			key = 'test_key'
			value = 'test_value'
			device.tags[key] = value
			device = client.update_device(collection.id, device)
			assert device.tags[key] == value

			assert len(client.device_data(collection.id, device.id)) == 0
		finally:
			client.delete_device(collection.id, device.id)
			devices = client.devices(collection.id)
			assert len(devices) == 0
	finally:
		client.delete_collection(collection.id)

def test_outputs():
	client = nbiot.Client()
	collection = client.create_collection(nbiot.Collection())

	try:
		output = client.create_output(collection.id, nbiot.WebHookOutput(url=nbiot.DEFAULT_ADDRESS))
		try:
			outputs = client.outputs(collection.id)
			assert contains(outputs, output)

			client.update_output(collection.id, output)

			assert len(client.output_logs(collection.id, output.id)) == 0
			client.output_status(collection.id, output.id)
		finally:
			client.delete_output(collection.id, output.id)
			outputs = client.outputs(collection.id)
			assert not contains(outputs, output)
	finally:
		client.delete_collection(collection.id)

@pytest.mark.asyncio
async def test_output_stream():
	client = nbiot.Client()
	collection = client.create_collection(nbiot.Collection())
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

@pytest.mark.skipif(os.environ.get('CI') != 'true', reason='downstream tests are slow')
def test_downstream():
	client = nbiot.Client()

	collection = client.create_collection(nbiot.Collection())
	devices = [client.create_device(collection.id, nbiot.Device(imsi=randid(), imei=randid())) for i in range(5)]
	try:
		with pytest.raises(nbiot.ClientError) as err:
			client.send(collection.id, devices[0].id, nbiot.DownstreamMessage(1234, b'Hello, device!'))
		assert err.value.http_status_code == requests.codes.conflict

		res = client.broadcast(collection.id, nbiot.DownstreamMessage(1234, b'Hello, devices!'))
		assert res.failed == len(devices)
	finally:
		[client.delete_device(collection.id, d.id) for d in devices]
		client.delete_collection(collection.id)

def randid():
	return str(random.randrange(1e15))

def contains(X, x):
	return any([y.id == x.id for y in X])