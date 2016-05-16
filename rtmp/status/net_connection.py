# Source code taken from rtmpy project (https://github.com/hydralabs/rtmpy):
# https://github.com/hydralabs/rtmpy/blob/master/rtmpy/status/codes.py

""" A list of all known NetConnection status codes and what they mean. """

#: The URI specified in the NetConnection.connect method did not specify 'rtmp'
#: as the protocol. 'rtmp' must be specified when connecting to an RTMP server.
#: Either not supported version of AMF was used (3 when only 0 is supported).
NC_CALL_BAD_VERSION = 'NetConnection.Call.BadVersion'

#: The NetConnection.call method was not able to invoke the server-side method
#: or command.
NC_CALL_FAILED = 'NetConnection.Call.Failed'

#: The application has been shut down (for example, if the application is out
#: of memory resources and must shut down to prevent the server from crashing)
#: or the server has shut down.
NC_CONNECT_APP_SHUTDOWN = 'NetConnection.Connect.AppShutdown'

#: The connection was closed successfully.
NC_CONNECT_CLOSED = 'NetConnection.Connect.Closed'

#: The connection attempt failed.
NC_CONNECT_FAILED = 'NetConnection.Connect.Failed'

#: The application name specified during connect is invalid.
NC_CONNECT_INVALID_APPLICATION = 'NetConnection.Connect.InvalidApp'

#: The client does not have permission to connect to the application, the
#: application expected different parameters from those that were passed,
#: or the application name specified during the connection attempt was not
#: found on the server.
NC_CONNECT_REJECTED = 'NetConnection.Connect.Rejected'

#: The connection attempt succeeded.
NC_CONNECT_SUCCESS = 'NetConnection.Connect.Success'
