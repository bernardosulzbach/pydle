import time
import pydle

from pytest import raises, mark
from .fixtures import with_client
from .mocks import Mock, MockEventLoop

pydle.client.PING_TIMEOUT = 10


## Initialization.

@with_client(invalid_kwarg=False)
def test_client_superfluous_arguments(server, client):
    assert client.logger.warning.called


## Connection.

@with_client()
def test_client_reconnect(server, client):
    client.disconnect(expected=True)
    assert not client.connected

    client.connect(reconnect=True)
    assert client.connected

@mark.slow
@with_client()
def test_client_unexpected_disconnect_reconnect(server, client):
    client._reconnect_delay = Mock(return_value=0)
    client.disconnect(expected=False)
    assert client._reconnect_delay.called

    time.sleep(0.1)
    assert client.connected

@with_client()
def test_client_unexpected_reconnect_give_up(server, client):
    client.RECONNECT_ON_ERROR = False
    client.disconnect(expected=False)
    assert not client.connected

@mark.slow
@with_client()
def test_client_unexpected_disconnect_reconnect_delay(server, client):
    client._reconnect_delay = Mock(return_value=1)
    client.disconnect(expected=False)

    assert not client.connected
    time.sleep(1.1)
    assert client.connected

@with_client()
def test_client_reconnect_delay_calculation(server, client):
    client.RECONNECT_DELAYED = False
    assert client._reconnect_delay() == 0

    client.RECONNECT_DELAYED = True
    for expected_delay in client.RECONNECT_DELAYS:
        delay = client._reconnect_delay()
        assert delay == expected_delay

        client._reconnect_attempts += 1

    assert client._reconnect_delay() == client.RECONNECT_DELAYS[-1]

@with_client()
def test_client_disconnect_on_connect(server, client):
    client.disconnect = Mock()

    client.connect('mock://local', 1337)
    assert client.connected
    assert client.disconnect.called

@with_client(connected=False)
def test_client_connect_invalid_params(server, client):
    with raises(ValueError):
        client.connect()
    with raises(ValueError):
        client.connect(port=1337)

@mark.slow
@with_client()
def test_client_timeout(server, client):
    client.on_data_error = Mock()
    time.sleep(pydle.client.PING_TIMEOUT + 1)

    assert client.on_data_error.called
    assert isinstance(client.on_data_error.call_args[0][0], TimeoutError)

@with_client(connected=False)
def test_client_server_tag(server, client):
    ev = MockEventLoop()
    assert client.server_tag is None

    client.connect('Mock.local', 1337, eventloop=ev)
    assert client.server_tag == 'mock'
    client.disconnect()

    client.connect('irc.mock.local', 1337, eventloop=ev)
    assert client.server_tag == 'mock'
    client.disconnect()

    client.connect('mock', 1337, eventloop=ev)
    assert client.server_tag == 'mock'
    client.disconnect()

    client.connect('127.0.0.1', 1337, eventloop=ev)
    assert client.server_tag == '127.0.0.1'

    client.network = 'MockNet'
    assert client.server_tag == 'mocknet'
    client.disconnect()


## Messages.

@with_client()
def test_client_message(server, client):
    client.on_raw_install = Mock()
    server.send('INSTALL', 'gentoo')
    assert client.on_raw_install.called

    message = client.on_raw_install.call_args[0][0]
    assert isinstance(message, pydle.protocol.Message)
    assert message.command == 'INSTALL'
    assert message.params == ('gentoo',)

@with_client()
def test_client_unknown(server, client):
    client.on_unknown = Mock()
    server.send('INSTALL', 'gentoo')
    assert client.on_unknown.called
