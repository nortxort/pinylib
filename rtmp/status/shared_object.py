# Source code taken from rtmpy project (https://github.com/hydralabs/rtmpy):
# https://github.com/hydralabs/rtmpy/blob/master/rtmpy/status/codes.py

""" A list of all known SharedObject status codes and what they mean. """

#: Read access to a shared object was denied.
SO_NO_READ_ACCESS = 'SharedObject.NoReadAccess'

#: Write access to a shared object was denied.
SO_NO_WRITE_ACCESS = 'SharedObject.NoWriteAccess'

#: The creation of a shared object was denied.
SO_CREATION_FAILED = 'SharedObject.ObjectCreationFailed'

#: The persistence parameter passed to SharedObject.getRemote() is
#: different from the one used when the shared object was created.
SO_PERSISTENCE_MISMATCH = 'SharedObject.BadPersistence'