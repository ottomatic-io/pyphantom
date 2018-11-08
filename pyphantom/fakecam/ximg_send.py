import codecs
import logging
import os
import pcapy
import struct

DEFAULT_TIMEOUT = 3

BPF_START = 0

logger = logging.getLogger(__name__)

frame_cache = {}

max_bytes = 1504
promiscuous = False
read_timeout = 1  # in millisecods
bufsize = 32  # in MB

pc = pcapy.open_live('lo0', max_bytes, promiscuous, read_timeout, bufsize)


def send_frame(cine, count, dest, ssrc):
    global frame_cache

    script_path = os.path.dirname(__file__)
    raw_path = os.path.join(script_path, './takes/{}.raw'.format(cine))

    try:
        frame_bytes = frame_cache[raw_path]
    except KeyError:
        frame_bytes = open(raw_path).read()
        frame_cache[raw_path] = frame_bytes

    to_mac = codecs.decode(dest, 'hex')
    from_mac = codecs.decode(b'feedfacebeef', 'hex')
    protocol = "\x88\xb7"
    version = '\x01'  # TODO: confirm if this is what gets sent by a cinestation
    sequence_number = 512
    timestamp = 0  # TODO: don't we want to use this somehow?
    unused = 0
    length = len(frame_bytes)

    for _ in range(count):
        view = memoryview(frame_bytes)
        start = '\x80'

        while len(view):
            header = struct.pack('>6s 6s 2s c c H I I H I',
                                 to_mac, from_mac, protocol, version, start, sequence_number,
                                 timestamp, ssrc, unused, length)

            ether_frame = header + view[:1468].tobytes()

            pc.sendpacket(ether_frame)
            view = view[1468:]
            sequence_number += 1
            if sequence_number > 65535:
                sequence_number = 0
            start = '\x00'


if __name__ == '__main__':
    with open(BPF_START, 'rb+') as s:
        initAndBindBPFSocket(s, 'lo0')
        send_frame(s)
