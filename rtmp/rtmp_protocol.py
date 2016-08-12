"""
Provides classes for creating RTMP (Real Time Message Protocol)
for servers and clients.

This is a edited rtmp-python version based on the original by prekageo
https://github.com/prekageo/rtmp-python
"""

import socket
import logging
import random
import time     # ping
import struct   # ping

import pyamf.amf0
import pyamf.amf3
import pyamf.util.pure

import rtmp_protocol_base
import types
import socks

log = logging.getLogger(__name__)


class FileDataTypeMixIn(pyamf.util.pure.DataTypeMixIn):
    """
    Provides a wrapper for a file object that enables reading and writing of raw
    data types for the file.
    """

    def __init__(self, fileobject):
        self.fileobject = fileobject
        pyamf.util.pure.DataTypeMixIn.__init__(self)

    def read(self, length):
        return self.fileobject.read(length)

    def write(self, data):
        self.fileobject.write(data)

    def flush(self):
        self.fileobject.flush()

    @staticmethod
    def at_eof():
        return False


class RtmpReader:
    """ This class reads RTMP messages from a stream. """

    # default chunk size
    chunk_size = 128

    def __init__(self, stream):
        """
        Initialize the RTMP reader and set it to read from the specified stream.
        """
        self.stream = stream
        self.prv_header = None

    def __iter__(self):
        return self

    def next(self):
        """ Read one RTMP message from the stream and return it. """
        if self.stream.at_eof():
            raise StopIteration
        # Read the message into body_stream. The message may span a number of
        # chunks (each one with its own header).
        message_body = []
        msg_body_len = 0
        header = rtmp_protocol_base.header_decode(self.stream)

        # FIXME: this should really be implemented inside header_decode
        if header.data_type == types.DT_NONE:
            header = self.prv_header
        self.prv_header = header

        while True:
            # NOTE: this whole loop section needs to be looked at.
            read_bytes = min(header.body_length - msg_body_len, self.chunk_size)

            message_body.append(self.stream.read(read_bytes))
            msg_body_len += read_bytes
            if msg_body_len >= header.body_length:
                break
            next_header = rtmp_protocol_base.header_decode(self.stream)
            # WORKAROUND: even though the RTMP specification states that the
            # extended timestamp field DOES NOT follow type 3 chunks, it seems
            # that Flash player 10.1.85.3 and Flash Media Server 3.0.2.217 send
            # and expect this field here.
            if header.timestamp >= 0x00ffffff:
                self.stream.read_ulong()
            assert next_header.stream_id == -1, (header, next_header)
            assert next_header.data_type == -1, (header, next_header)
            assert next_header.timestamp == -1, (header, next_header)
            assert next_header.body_length == -1, (header, next_header)
        assert header.body_length == msg_body_len, (header, msg_body_len)
        body_stream = pyamf.util.BufferedByteStream(''.join(message_body))

        # Decode the message based on the datatype present in the header
        ret = {'msg': header.data_type}
        if ret['msg'] == types.DT_USER_CONTROL:
            log.debug('DT_USER_CONTROL: %s Header: %s' % (ret['msg'], header))
            # BUG: sometimes i get event_type = 512 in RtmpClient.handle_packet
            # this seems to only happen when using PING requests to keep the bot alive with.
            ret['event_type'] = body_stream.read_ushort()
            ret['event_data'] = body_stream.read()

        elif ret['msg'] == types.DT_WINDOW_ACK_SIZE:
            ret['window_ack_size'] = body_stream.read_ulong()

        elif ret['msg'] == types.DT_SET_PEER_BANDWIDTH:
            ret['window_ack_size'] = body_stream.read_ulong()
            ret['limit_type'] = body_stream.read_uchar()

        elif ret['msg'] == types.DT_SHARED_OBJECT:
            decoder = pyamf.amf0.Decoder(body_stream)
            obj_name = decoder.readString()
            curr_version = body_stream.read_ulong()
            flags = body_stream.read(8)
            # A shared object message may contain a number of events.
            events = []
            while not body_stream.at_eof():
                event = self.read_shared_object_event(body_stream, decoder)
                events.append(event)

            ret['obj_name'] = obj_name
            ret['curr_version'] = curr_version
            ret['flags'] = flags
            ret['events'] = events

        elif ret['msg'] == types.DT_AMF3_SHARED_OBJECT:
            decoder = pyamf.amf3.Decoder(body_stream)
            obj_name = decoder.readString()
            curr_version = body_stream.read_ulong()
            flags = body_stream.read(8)
            # A shared object message may contain a number of events.
            events = []
            while not body_stream.at_eof():
                event = self.read_shared_object_event(body_stream, decoder)
                events.append(event)

            ret['obj_name'] = obj_name
            ret['curr_version'] = curr_version
            ret['flags'] = flags
            ret['events'] = events

        elif ret['msg'] == types.DT_COMMAND:
            decoder = pyamf.amf0.Decoder(body_stream)
            commands = []
            while not body_stream.at_eof():
                commands.append(decoder.readElement())
            ret['command'] = commands

        elif ret['msg'] == types.DT_AMF3_COMMAND:
            decoder = pyamf.amf3.Decoder(body_stream)
            commands = []
            while not body_stream.at_eof():
                commands.append(decoder.readElement())
            ret['command'] = commands

        elif ret['msg'] == types.DT_NONE:
            log.warning('WARNING: message with no datatype received: %s' % header)
            return self.next()

        elif ret['msg'] == types.DT_SET_CHUNK_SIZE:
            ret['chunk_size'] = body_stream.read_ulong()
        else:
            assert False, header

        log.debug('recv %r', ret)
        return ret

    @staticmethod
    def read_shared_object_event(body_stream, decoder):
        """
        Helper method that reads one shared object event found inside a shared
        object RTMP message.
        """
        so_body_type = body_stream.read_uchar()
        so_body_size = body_stream.read_ulong()

        event = {'type': so_body_type}
        if event['type'] == types.SO_USE:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == types.SO_RELEASE:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == types.SO_CHANGE:
            start_pos = body_stream.tell()
            changes = {}
            while body_stream.tell() < start_pos + so_body_size:
                attrib_name = decoder.readString()
                attrib_value = decoder.readElement()
                assert attrib_name not in changes, (attrib_name, changes.keys())
                changes[attrib_name] = attrib_value
            assert body_stream.tell() == start_pos + so_body_size,\
                (body_stream.tell(), start_pos, so_body_size)
            event['data'] = changes

        elif event['type'] == types.SO_SEND_MESSAGE:
            start_pos = body_stream.tell()
            msg_params = []
            while body_stream.tell() < start_pos + so_body_size:
                msg_params.append(decoder.readElement())
            assert body_stream.tell() == start_pos + so_body_size,\
                (body_stream.tell(), start_pos, so_body_size)
            event['data'] = msg_params

        elif event['type'] == types.SO_CLEAR:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        elif event['type'] == types.SO_REMOVE:
            event['data'] = decoder.readString()

        elif event['type'] == types.SO_USE_SUCCESS:
            assert so_body_size == 0, so_body_size
            event['data'] = ''

        else:
            assert False, event['type']

        return event


class RtmpWriter:
    """ This class writes RTMP messages into a stream. """

    # default chunk size
    chunk_size = 128

    def __init__(self, stream):
        """ Initialize the RTMP writer and set it to write into the specified stream. """
        self.stream = stream

    def flush(self):
        """ Flush the underlying stream. """
        self.stream.flush()

    def write(self, message):
        log.debug('send %r', message)
        """ Encode and write the specified message into the stream. """
        datatype = message['msg']
        body_stream = pyamf.util.BufferedByteStream()
        encoder = pyamf.amf0.Encoder(body_stream)

        if datatype == types.DT_USER_CONTROL:
            body_stream.write_ushort(message['event_type'])
            body_stream.write(message['event_data'])
            self.send_msg(datatype, body_stream.getvalue())

        elif datatype == types.DT_WINDOW_ACK_SIZE:
            body_stream.write_ulong(message['window_ack_size'])
            self.send_msg(datatype, body_stream.getvalue())

        elif datatype == types.DT_SET_PEER_BANDWIDTH:
            body_stream.write_ulong(message['window_ack_size'])
            body_stream.write_uchar(message['limit_type'])
            self.send_msg(datatype, body_stream.getvalue())

        elif datatype == types.DT_COMMAND:
            for command in message['command']:
                encoder.writeElement(command)
            if 'createStream' in message['command']:
                self.send_msg(datatype, body_stream.getvalue())
            elif 'closeStream' in message['command']:
                self.send_msg(datatype, body_stream.getvalue(), ch_id=11, st_id=1)
            elif 'deleteStream' in message['command']:
                self.send_msg(datatype, body_stream.getvalue(), ch_id=1, st_id=3)
            elif 'publish' in message['command']:
                self.send_msg(datatype, body_stream.getvalue(), ch_id=11, st_id=1)
            elif 'play' in message['command']:
                self.send_msg(datatype, body_stream.getvalue(), ch_id=1, st_id=8)
            else:
                self.send_msg(datatype, body_stream.getvalue())

        elif datatype == types.DT_AMF3_COMMAND:
            encoder = pyamf.amf3.Encoder(body_stream)
            for command in message['command']:
                encoder.writeElement(command)
            self.send_msg(datatype, body_stream.getvalue())

        elif datatype == types.DT_SHARED_OBJECT:
            encoder.serialiseString(message['obj_name'])
            body_stream.write_ulong(message['curr_version'])
            body_stream.write(message['flags'])

            for event in message['events']:
                self.write_shared_object_event(event, body_stream)
            self.send_msg(datatype, body_stream.getvalue())
        else:
            assert False, message

        # self.send_msg(datatype, body_stream.getvalue())

    @staticmethod
    def write_shared_object_event(event, body_stream):
        inner_stream = pyamf.util.BufferedByteStream()
        encoder = pyamf.amf0.Encoder(inner_stream)

        event_type = event['type']
        if event_type == types.SO_USE:
            assert event['data'] == '', event['data']

        elif event_type == types.SO_CHANGE:
            for attrib_name in event['data']:
                attrib_value = event['data'][attrib_name]
                encoder.serialiseString(attrib_name)
                encoder.writeElement(attrib_value)

        elif event['type'] == types.SO_CLEAR:
            assert event['data'] == '', event['data']

        elif event['type'] == types.SO_USE_SUCCESS:
            assert event['data'] == '', event['data']

        else:
            assert False, event

        body_stream.write_uchar(event_type)
        body_stream.write_ulong(len(inner_stream))
        body_stream.write(inner_stream.getvalue())

    def send_msg(self, data_type, body, ch_id=3, st_id=0, timestamp=0):
        """
        Helper method that send the specified message into the stream. Takes
        care to prepend the necessary headers and split the message into
        appropriately sized chunks.
        """
        # Values that just work. :-)
        if 1 <= data_type <= 7:
            channel_id = 2
            stream_id = 0
        else:
            channel_id = ch_id
            stream_id = st_id
        timestamp = timestamp

        header = rtmp_protocol_base.Header(
            channel_id=channel_id,
            stream_id=stream_id,
            data_type=data_type,
            body_length=len(body),
            timestamp=timestamp)
        rtmp_protocol_base.header_encode(self.stream, header)

        for i in xrange(0, len(body), self.chunk_size):
            chunk = body[i:i + self.chunk_size]
            self.stream.write(chunk)
            if i+self.chunk_size < len(body):
                rtmp_protocol_base.header_encode(self.stream, header, header)


class FlashSharedObject:
    """
    This class represents a Flash Remote Shared Object. Its data are located
    inside the self.data dictionary.
    """

    def __init__(self, name):
        """ Initialize a new Flash Remote SO with a given name and empty data."""
        self.name = name
        self.data = {}
        self.use_success = False

    def use(self, writer):
        """
        Initialize usage of the SO by contacting the Flash Media Server. Any
        remote changes to the SO should be now propagated to the client.
        """
        self.use_success = False

        msg = {
            'msg': types.DT_SHARED_OBJECT,
            'curr_version': 0,
            'flags': '\x00\x00\x00\x00\x00\x00\x00\x00',
            'events': [
                {
                    'data': '',
                    'type': types.SO_USE
                }
            ],
            'obj_name': self.name
        }
        writer.write(msg)
        writer.flush()

    def handle_message(self, message):
        """
        Handle an incoming RTMP message. Check if it is of any relevance for the
        specific SO and process it, otherwise ignore it.
        """
        if message['msg'] == types.DT_SHARED_OBJECT and message['obj_name'] == self.name:
            events = message['events']

            if not self.use_success:
                assert events[0]['type'] == types.SO_USE_SUCCESS, events[0]
                assert events[1]['type'] == types.SO_CLEAR, events[1]
                events = events[2:]
                self.use_success = True

            self.handle_events(events)
            return True
        else:
            return False

    def handle_events(self, events):
        """ Handle SO events that target the specific SO. """
        for event in events:
            event_type = event['type']
            if event_type == types.SO_CHANGE:
                for key in event['data']:
                    self.data[key] = event['data'][key]
                    self.on_change(key)
            elif event_type == types.SO_REMOVE:
                key = event['data']
                assert key in self.data, (key, self.data.keys())
                del self.data[key]
                self.on_delete(key)
            elif event_type == types.SO_SEND_MESSAGE:
                self.on_message(event['data'])
            else:
                assert False, event

    def on_change(self, key):
        pass

    def on_delete(self, key):
        pass

    def on_message(self, data):
        pass


class RtmpClient:
    """ Represents an RTMP client. """
    def __init__(self, ip, port, tc_url, page_url, swf_url, app, proxy=None):
        """ Initialize a new RTMP client. """
        self.ip = ip
        self.port = port
        self.tc_url = tc_url
        self.page_url = page_url
        self.swf_url = swf_url
        self.app = app
        self.proxy = proxy
        self.flash_version = 'WIN 21.0.0.197'
        self.shared_objects = []
        self.socket = None
        self.stream = None
        self.file = None
        self.writer = None
        self.reader = None

    @staticmethod
    def create_random_bytes(length, readable=False):
        """ Creates random bytes for the handshake. """
        ran_bytes = ''
        i, j = 0, 0xff
        if readable:
            i, j = 0x41, 0x7a
        for x in xrange(0, length):
            ran_bytes += chr(random.randint(i, j))
        return ran_bytes

    def handshake(self):
        """ Perform the handshake sequence with the server. """
        self.stream.write_uchar(3)
        c1 = rtmp_protocol_base.Packet()
        c1.first = 0
        c1.second = 0
        c1.payload = self.create_random_bytes(1528)
        c1.encode(self.stream)
        self.stream.flush()

        self.stream.read_uchar()
        s1 = rtmp_protocol_base.Packet()
        s1.decode(self.stream)

        c2 = rtmp_protocol_base.Packet()
        c2.first = s1.first
        c2.second = s1.second
        c2.payload = s1.payload
        c2.encode(self.stream)
        self.stream.flush()

        s2 = rtmp_protocol_base.Packet()
        s2.decode(self.stream)

    def connect_rtmp(self, connect_params):
        """ Initiate a NetConnection with a Flash Media Server. """
        msg = {
            'msg': types.DT_COMMAND,
            'command':
            [
                u'connect',
                1,
                {
                    'videoCodecs': 252,
                    'audioCodecs': 3575,
                    'flashVer': u'' + self.flash_version,
                    'app': self.app,
                    'tcUrl': self.tc_url,
                    'videoFunction': 1,
                    'capabilities': 239,
                    'pageUrl': self.page_url,
                    'fpad': False,
                    'swfUrl': self.swf_url,
                    'objectEncoding': 0
                }
            ]
        }
        if type(connect_params) is dict:
            msg['command'].append(connect_params)
        else:
            msg['command'].extend(connect_params)

        self.writer.write(msg)
        self.writer.flush()

    def handle_packet(self, amf_data):
        """ Handle packets based on data type."""
        if amf_data['msg'] == types.DT_USER_CONTROL and amf_data['event_type'] == types.UC_PING_REQUEST:
            resp = {
                'msg': types.DT_USER_CONTROL,
                'event_type': types.UC_PING_RESPONSE,
                'event_data': amf_data['event_data'],
            }
            self.writer.write(resp)
            self.writer.flush()
            return True

        elif amf_data['msg'] == types.DT_USER_CONTROL and amf_data['event_type'] == types.UC_PING_RESPONSE:
            unpacked_tpl = struct.unpack('>I', amf_data['event_data'])
            unpacked_response = unpacked_tpl[0]
            log.debug('ping response from server %s' % unpacked_response)
            return True

        elif amf_data['msg'] == types.DT_WINDOW_ACK_SIZE:
            assert amf_data['window_ack_size'] == 2500000, amf_data
            ack_msg = {'msg': types.DT_WINDOW_ACK_SIZE, 'window_ack_size': amf_data['window_ack_size']}
            self.writer.write(ack_msg)
            self.writer.flush()
            return True

        elif amf_data['msg'] == types.DT_SET_PEER_BANDWIDTH:
            assert amf_data['window_ack_size'] == 2500000, amf_data
            assert amf_data['limit_type'] == 2, amf_data
            return True

        elif amf_data['msg'] == types.DT_USER_CONTROL and amf_data['event_type'] == types.UC_STREAM_BEGIN:
            assert amf_data['event_type'] == types.UC_STREAM_BEGIN, amf_data
            assert amf_data['event_data'] == '\x00\x00\x00\x00', amf_data
            return True

        elif amf_data['msg'] == types.DT_SET_CHUNK_SIZE:
            assert 0 < amf_data['chunk_size'] <= 65536, amf_data
            self.reader.chunk_size = amf_data['chunk_size']
            return True

        else:
            return False

    def call(self, process_name, parameters=None, trans_id=0):
        """ Runs remote procedure calls (RPC) at the receiving end. """
        if parameters is None:
            parameters = {}
        msg = {
            'msg': types.DT_COMMAND,
            'command':
            [
                process_name,
                trans_id,
                parameters
            ]
        }
        self.writer.write(msg)
        self.writer.flush()

    def connect(self, connect_params=None):
        """ Connect to the server with the given connect parameters. """
        if self.proxy:
            parts = self.proxy.split(':')
            ip = parts[0]
            port = int(parts[1])

            ps = socks.socksocket()
            ps.set_proxy(socks.HTTP, addr=ip, port=port)
            self.socket = ps
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.socket.connect((self.ip, self.port))
        self.file = self.socket.makefile()
        self.stream = FileDataTypeMixIn(self.file)

        self.handshake()

        self.reader = RtmpReader(self.stream)
        self.writer = RtmpWriter(self.stream)

        self.connect_rtmp(connect_params)

    def shutdown(self):
        """ Closes the socket connection. """
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def shared_object_use(self, so):
        """ Use a shared object and add it to the managed list of SOs. """
        if so in self.shared_objects:
            return
        so.use(self.reader, self.writer)
        self.shared_objects.append(so)

    def send_ping_request(self):
        """
        Send a PING request.
        NOTE: I think its highly unlikely that a client would send this to a server,
        it's usally the other way around, the sever sends this to the client to make sure the client is alive.
        It does seem like some servers(all?) respond to this.
        """
        msg = {
            'msg': types.DT_USER_CONTROL,
            'event_type': types.UC_PING_REQUEST,
            'event_data': struct.pack('>I', int(time.time()))
        }
        log.debug('sending ping request to server: %s' % msg)
        self.writer.write(msg)
        self.writer.flush()
