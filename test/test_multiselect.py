import asyncio
import pytest
from multistream_select.multiselect import Multiselect, MultiselectError
from multistream_select.multiselect_client import MultiselectClient, \
    MultiselectClientError, MULTISELECT_PROTOCOL_ID
from multistream_select.multiselect_communicator import \
    MultiselectCommunicator


class SimpleSockStream:
    def __init__(self):
        self.write = None
        self.incoming = []

    async def read(self):
        attempt = 0
        while not self.incoming:
            if attempt == 5:
                raise TimeoutError
            await asyncio.sleep(0.2)
            attempt += 1
        return self.incoming.pop(0)

    def connect(self, target):
        # assert isinstance(target, SimpleSock)
        self.write = target.writetome

    async def writetome(self, msg):
        # To be called by connected
        self.incoming.append(msg)


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


def create_network():
    h_s = SimpleSockStream()
    c_s = SimpleSockStream()
    h_s.connect(c_s)
    c_s.connect(h_s)
    return h_s, c_s


async def perform_simple_test(expected_selected_protocol, protocols_for_client,
                              protocols_with_handlers, args=None):
    default = {
        "select-single": False
    }

    if args is None:
        args = default

    host_stream, client_stream = create_network()

    host_ms = Multiselect()
    for protocol in protocols_with_handlers:
        host_ms.add_handler(protocol, None)
    client_ms = MultiselectClient()

    if args['select-single']:
        func = client_ms.select_protocol_or_fail

    else:
        func = client_ms.select_one_of

    result = await asyncio.gather(
        func(protocols_for_client, client_stream),
        host_ms.negotiate(host_stream)
    )
    assert result[0] == expected_selected_protocol


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


@pytest.mark.asyncio
async def test_host_handshake_fail():
    stream = InvalidHandshakeStream()
    comm = MultiselectCommunicator(stream)
    host = Multiselect()
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


@pytest.mark.asyncio
async def test_host_ls():

    class StrStream:
        def __init__(self, istream):
            self.super = istream

        async def write(self, msg):
            await self.super.write(msg.encode())

        async def read(self):
            return (await self.super.read()).decode()

    protocols = ['/egg/1.0', '/plant/1.0', '/echo/1.0']

    host_stream, client_stream = create_network()
    host = Multiselect()

    for protocol in protocols:
        host.add_handler(protocol, None)

    stream = StrStream(client_stream)
    loop = asyncio.get_event_loop()
    task = loop.create_task(host.negotiate(host_stream))

    await stream.write(MULTISELECT_PROTOCOL_ID)  # handshake
    assert await stream.read() == MULTISELECT_PROTOCOL_ID
    await stream.write("ls")  # send ls (expect nothing)

    try:
        response = await stream.read()
    except TimeoutError:
        pass

    assert response.split('\n') == protocols
    with pytest.raises(TimeoutError):
        await task
