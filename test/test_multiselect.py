import pytest
import socket
import threading
import asyncio
import time
from multistream_select.multiselect import Multiselect
from multistream_select.multiselect_client import MultiselectClient, MultiselectClientError


class StreamI:
    def __init__(self, sock, id):
        self.id = id
        self.stream = sock.makefile('rwb')

    async def read(self):
        print(self.id, 'reading')
        length = int.from_bytes(self.stream.read(1), byteorder='big')
        return self.stream.read(length)

    async def write(self, b):
        print(self.id, 'writes', b)
        self.stream.write(len(b).to_bytes(1,byteorder='big'))
        r = self.stream.write(b)
        print(len(bytes([len(b)])))
        assert len(b) == r
        self.stream.flush()
        print(self.id, 'written', r)
        return r


async def perform_simple_test(expected_selected_protocol,
                              protocols_for_client, protocols_with_handlers):
    addr = ('localhost', 10000)

    def host_coroute():
        def empty_handler():
            pass

        host_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host_sock.bind(addr)
        host_sock.listen(1)
        hconn, _ = host_sock.accept()
        host_stream = StreamI(hconn, 'host')
        host = Multiselect()
        for p in protocols_with_handlers:
            host.add_handler(p, empty_handler)
        iloop = asyncio.new_event_loop()
        iloop.run_until_complete(host.negotiate(host_stream))
        host_sock.close()

    t = threading.Thread(target=host_coroute)
    t.start()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(addr)
    stream = StreamI(sock, 'client')
    client_ms = MultiselectClient()
    print(t.is_alive())
    try:
        protocol = await client_ms.select_one_of(protocols_for_client, stream)
        sock.close()
    except MultiselectClientError:
        await stream.write('debug-sigkill'.encode())  # kill host
        t.join()
        sock.close()
        raise MultiselectClientError
    assert protocol == expected_selected_protocol


@pytest.mark.asyncio
async def test_single_protocol_succeeds():
    expected_selected_protocol = "/echo/1.0.0"
    await perform_simple_test(expected_selected_protocol,
                              ["/echo/1.0.0"], ["/echo/1.0.0"])


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
    protocols_for_listener = ["/aspyn/1.0.0", "/rob/1.0.0", "/zx/1.0.0", "/alex/1.0.0"]
    with pytest.raises(MultiselectClientError):
        await perform_simple_test("", protocols_for_client,
                                  protocols_for_listener)
