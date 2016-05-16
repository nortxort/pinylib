"""
Source code taken from rtmpy project (http://rtmpy.org/):
rtmpy/protocol/handshake.py
rtmpy/protocol/rtmp/header.py

This is a edited version of rtmp-python based on the original by prekageo
https://github.com/prekageo/rtmp-python
"""
import logging
import time

HANDSHAKE_LENGTH = 1536

log = logging.getLogger(__name__)


class Packet(object):
    """
    A handshake packet.

    @ivar first: The first 4 bytes of the packet, represented as an unsigned
        long.
    @type first: 32bit unsigned int.
    @ivar second: The second 4 bytes of the packet, represented as an unsigned
        long.
    @type second: 32bit unsigned int.
    @ivar payload: A blob of data which makes up the rest of the packet. This
        must be C{HANDSHAKE_LENGTH} - 8 bytes in length.
    @type payload: C{str}
    @ivar timestamp: Timestamp that this packet was created (in milliseconds).
    @type timestamp: C{int}
    """

    first = None
    second = None
    payload = None
    timestamp = None

    def __init__(self, **kwargs):
        timestamp = kwargs.get('timestamp', None)

        if timestamp is None:
            kwargs['timestamp'] = int(time.time())

        self.__dict__.update(kwargs)

    def encode(self, stream_buffer):
        """
        Encodes this packet to a stream.
        """
        stream_buffer.write_ulong(self.first or 0)
        stream_buffer.write_ulong(self.second or 0)

        stream_buffer.write(self.payload)

    def decode(self, stream_buffer):
        """
        Decodes this packet from a stream.
        """
        self.first = stream_buffer.read_ulong()
        self.second = stream_buffer.read_ulong()

        self.payload = stream_buffer.read(HANDSHAKE_LENGTH - 8)


def header_decode(stream):
    """
    Reads a header from the incoming stream.

    A header can be of varying lengths and the properties that get updated
    depend on the length.

    @param stream: The byte stream to read the header from.
    @type stream: C{pyamf.util.BufferedByteStream}
    @return: The read header from the stream.
    @rtype: L{Header}
    """
    # read the size and channel_id
    channel_id = stream.read_uchar()
    bits = channel_id >> 6
    channel_id &= 0x3f

    if channel_id == 0:
        channel_id = stream.read_uchar() + 64

    if channel_id == 1:
        channel_id = stream.read_uchar() + 64 + (stream.read_uchar() << 8)

    header = Header(channel_id)

    if bits == 3:
        return header

    header.timestamp = stream.read_24bit_uint()

    if bits < 2:
        header.body_length = stream.read_24bit_uint()
        header.data_type = stream.read_uchar()

    if bits < 1:
        # streamId is little endian
        stream.endian = '<'
        header.stream_id = stream.read_ulong()
        stream.endian = '!'

        header.full = True

    if header.timestamp == 0xffffff:
        header.timestamp = stream.read_ulong()

    log.info('header recv: %s' % header)
    return header


def header_encode(stream, header, previous=None):
    """
    Encodes a RTMP header to C{stream}.

    We expect the stream to already be in network endian mode.

    The channel id can be encoded in up to 3 bytes. The first byte is special as
    it contains the size of the rest of the header as described in
    L{getHeaderSize}.

    0 >= channel_id > 64: channel_id
    64 >= channel_id > 320: 0, channel_id - 64
    320 >= channel_id > 0xffff + 64: 1, channel_id - 64 (written as 2 byte int)

    @param stream: The stream to write the encoded header.
    @type stream: L{util.BufferedByteStream}
    @param header: The L{Header} to encode.
    @param previous: The previous header (if any).
    """
    log.debug('header send: %s' % header)
    if previous is None:
        size = 0
    else:
        size = min_bytes_required(header, previous)

    channel_id = header.channel_id

    if channel_id < 64:
        stream.write_uchar(size | channel_id)
    elif channel_id < 320:
        stream.write_uchar(size)
        stream.write_uchar(channel_id - 64)
    else:
        channel_id -= 64

        stream.write_uchar(size + 1)
        stream.write_uchar(channel_id & 0xff)
        stream.write_uchar(channel_id >> 0x08)

    if size == 0xc0:
        return

    if size <= 0x80:
        if header.timestamp >= 0xffffff:
            stream.write_24bit_uint(0xffffff)
        else:
            stream.write_24bit_uint(header.timestamp)

    if size <= 0x40:
        stream.write_24bit_uint(header.body_length)
        stream.write_uchar(header.data_type)

    if size == 0:
        stream.endian = '<'
        stream.write_ulong(header.stream_id)
        stream.endian = '!'

    if size <= 0x80:
        if header.timestamp >= 0xffffff:
            stream.write_ulong(header.timestamp)


class Header(object):
    """
    An RTMP Header. Holds contextual information for an RTMP Channel.
    """

    __slots__ = ('stream_id', 'data_type', 'timestamp',
                 'body_length', 'channel_id', 'full')

    def __init__(self, channel_id, timestamp=-1, data_type=-1,
                 body_length=-1, stream_id=-1, full=False):
        self.channel_id = channel_id
        self.timestamp = timestamp
        self.data_type = data_type
        self.body_length = body_length
        self.stream_id = stream_id
        self.full = full

    def __repr__(self):
        attrs = []

        for k in self.__slots__:
            v = getattr(self, k, None)

            if v == -1:
                v = None

            attrs.append('%s=%r' % (k, v))

        return '<%s.%s %s at 0x%x>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            ' '.join(attrs),
            id(self))


def min_bytes_required(old, new):
    """
    Returns the number of bytes needed to de/encode the header based on the
    differences between the two.

    Both headers must be from the same channel.

    @type old: L{Header}
    @type new: L{Header}
    """
    if old is new:
        return 0xc0

    if old.channel_id != new.channel_id:
        raise Exception('HeaderError: channel_id mismatch on diff old=%r, new=%r' % (old, new))

    if old.stream_id != new.stream_id:
        return 0  # full header

    if old.data_type == new.data_type and old.body_length == new.body_length:
        if old.timestamp == new.timestamp:
            return 0xc0

        return 0x80

    return 0x40
