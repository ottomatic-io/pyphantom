import codecs
import logging
import os
import pcapy
import struct

DEFAULT_TIMEOUT = 3
BPF_START = 0

logger = logging.getLogger(__name__)
frame_cache = {}

pc = pcapy.create("lo0")
pc.set_snaplen(1504)
pc.set_promisc(False)
pc.set_timeout(1)  # in millisecods
pc.set_buffer_size(32 * 1024 * 1024)
pc.activate()


def send_frame(cine, count, dest, ssrc):
    global frame_cache

    script_path = os.path.dirname(__file__)
    raw_path = os.path.join(script_path, "./takes/{}.raw".format(cine))

    try:
        frame_bytes = frame_cache[raw_path]
    except KeyError:
        frame_bytes = open(raw_path).read()
        frame_cache[raw_path] = frame_bytes

    to_mac = codecs.decode(dest, "hex")
    from_mac = codecs.decode(b"feedfacebeef", "hex")
    protocol = "\x88\xb7"
    version = "\x01"
    sequence_number = 512
    timestamp = 0  # TODO: don't we want to use this somehow?
    unused = 0
    length = len(frame_bytes)

    for _ in range(count):
        view = memoryview(frame_bytes)
        start = "\x80"

        while len(view):
            header = struct.pack(
                ">6s 6s 2s c c H I I H I",
                to_mac,
                from_mac,
                protocol,
                version,
                start,
                sequence_number,
                timestamp,
                ssrc,
                unused,
                length,
            )

            ether_frame = header + view[:1468].tobytes()

            pc.sendpacket(ether_frame)
            view = view[1468:]
            sequence_number += 1
            if sequence_number > 65535:
                sequence_number = 0
            start = "\x00"
