import socket
import threading
import asyncio
import pytest
from multistream_select.multiselect import Multiselect, MultiselectError
from multistream_select.multiselect_client import MultiselectClient, \
    MultiselectClientError, MULTISELECT_PROTOCOL_ID
from multistream_select.multiselect_communicator import \
    MultiselectCommunicator


# TODO: HOST: debug-sigkill without debug flag, ls,


class StreamI:
    """
    Stream interface to enforce protocol for tcp connection
    """

    def __init__(self, sock, timeout=False):
        self.sock = sock
        self.stream = sock.makefile('rwb')
        self.timeout = timeout
        self.msgs = []

    async def read(self):
        in_b = self.stream.read(1)
        length = int.from_bytes(in_b, byteorder='big')
        return self.stream.read(length)

    async def write(self, bytes_towrite):
        self.stream.write(len(bytes_towrite).to_bytes(1, byteorder='big'))
        result = self.stream.write(bytes_towrite)
        assert len(bytes_towrite) == result
        self.stream.flush()
        return result

    def close(self):
        self.stream.close()
        self.stream = None


def create_host_process(protocols=None, debug=True, streamtimeout=False):
    """
    Create a Multiselect host thread
    :param protocols: list of protocols supported (empty handler)
    :param debug: Multiselect debug mode (default: True)
    :param streamtimeout: Host stream timeout (default: False)
    :return: (threading.Thread) process
    """
    if protocols is None:
        protocols = []
    host_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host_sock.bind(('0.0.0.0', 0))

    def host_coroute():
        def empty_handler():
            pass

        host_sock.listen(1)
        hconn, _ = host_sock.accept()
        host_stream = StreamI(hconn, timeout=streamtimeout)
        host = Multiselect(debug=debug)
        for protocol in protocols:
            host.add_handler(protocol, empty_handler)
        iloop = asyncio.new_event_loop()
        iloop.run_until_complete(host.negotiate(host_stream))
        host_stream.close()
        host_sock.close()

    thread = threading.Thread(target=host_coroute)
    return thread, host_sock


async def perform_simple_test(expected_selected_protocol, protocols_for_client,
                              protocols_with_handlers, args=None):
    default = {
        "select-single": False
    }

    if args is None:
        args = default

    thread, host_sock = create_host_process(protocols_with_handlers)
    thread.start()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', host_sock.getsockname()[1]))
    stream = StreamI(sock)
    client_ms = MultiselectClient()
    try:
        if args['select-single']:
            protocol = await client_ms.select_protocol_or_fail(
                protocols_for_client, stream)
        else:
            protocol = await client_ms.select_one_of(protocols_for_client, stream)
        stream.close()
        sock.close()
    except MultiselectClientError:
        await stream.write('debug-sigkill'.encode())  # kill host
        thread.join()
        stream.close()
        sock.close()
        raise MultiselectClientError
    assert protocol == expected_selected_protocol


@pytest.mark.asyncio
async def test_single_protocol_succeeds():
    expected_selected_protocol = "/echo/1.0.0"
    await perform_simple_test(expected_selected_protocol,
                              ["/echo/1.0.0"], ["/echo/1.0.0"])


@pytest.mark.asyncio
async def test_single_protocol_with_selectorfail_succeeds():
    expected_selected_protocol = "/echo/1.0.0"
    args = {"select-single": True}
    await perform_simple_test(expected_selected_protocol,
                              "/echo/1.0.0", ["/echo/1.0.0"], args)


@pytest.mark.asyncio
async def test_single_protocol_fails():
    with pytest.raises(MultiselectClientError):
        await perform_simple_test("", ["/echo/1.0.0"],
                                  ["/potato/1.0.0"])


@pytest.mark.asyncio
async def test_multiple_protocol_first_is_valid_succeeds():
    expected_selected_protocol = "/echo/1.0.0"
    protocols_for_client = ["/echo/1.0.0", "/potato/1.0.0"]
    protocols_for_listener = ["/foo/1.0.0", "/echo/1.0.0"]
    await perform_simple_test(expected_selected_protocol, protocols_for_client,
                              protocols_for_listener)


@pytest.mark.asyncio
async def test_multiple_protocol_second_is_valid_succeeds():
    expected_selected_protocol = "/foo/1.0.0"
    protocols_for_client = ["/rock/1.0.0", "/foo/1.0.0"]
    protocols_for_listener = ["/foo/1.0.0", "/echo/1.0.0"]
    await perform_simple_test(expected_selected_protocol, protocols_for_client,
                              protocols_for_listener)


@pytest.mark.asyncio
async def test_multiple_protocol_fails():
    protocols_for_client = ["/rock/1.0.0", "/foo/1.0.0", "/bar/1.0.0"]
    protocols_for_listener = ["/aspyn/1.0.0", "/rob/1.0.0", "/zx/1.0.0",
                              "/alex/1.0.0"]
    with pytest.raises(MultiselectClientError):
        await perform_simple_test("", protocols_for_client,
                                  protocols_for_listener)


class InvalidHandshakeStream:
    """
    Valid User: Client, Host
    Always return an invalid HANDSHAKE version, does not interface StreamI
    """

    def __init__(self):
        pass

    @staticmethod
    async def read():
        return (MULTISELECT_PROTOCOL_ID + '.1').encode()

    @staticmethod
    async def write(byte):
        return len(byte)


class UnknownResponseStream:
    """
    Valid User: Client
    Pass handshake and send nonsense to client
    """

    def __init__(self):
        self.msgs = [MULTISELECT_PROTOCOL_ID,
                     'you dont know me']

    async def read(self):
        return self.msgs.pop(0).encode()

    @staticmethod
    async def write(byte):
        return len(byte)


@pytest.mark.asyncio
async def test_host_handshake_fail():
    stream = InvalidHandshakeStream()
    comm = MultiselectCommunicator(stream)
    host = Multiselect(debug=True)
    with pytest.raises(MultiselectError):
        await host.handshake(comm)


@pytest.mark.asyncio
async def test_client_handshake_fail():
    stream = InvalidHandshakeStream()
    comm = MultiselectCommunicator(stream)
    client = MultiselectClient()
    with pytest.raises(MultiselectClientError):
        await client.handshake(comm)


@pytest.mark.asyncio
async def test_client_unknown_response():
    stream = UnknownResponseStream()
    client = MultiselectClient()
    with pytest.raises(MultiselectClientError):
        await client.select_protocol_or_fail("/echo/1.0", stream)


'''
@pytest.mark.asyncio
async def test_host_commands_handling():
    t, host_sock = create_host_process([], False, True)
    t.start()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', host_sock.getsockname()[1]))

    class StrStream(StreamI):
        async def write(self, s):
            await super().write(s.encode())

        async def read(self):
            return (await super().read()).decode()

    stream = StrStream(sock)
    await stream.write(MULTISELECT_PROTOCOL_ID)  # handshake
    assert await stream.read() == MULTISELECT_PROTOCOL_ID
    time.sleep(1)
    await stream.write("ls")  # send ls (expect nothing)
    await stream.write("debug-sigkill")  # expect alive
    assert t.is_alive()
'''
