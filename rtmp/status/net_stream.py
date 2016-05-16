# Source code taken from rtmpy project (https://github.com/hydralabs/rtmpy):
# https://github.com/hydralabs/rtmpy/blob/master/rtmpy/status/codes.py

""" A list of all known NetStream status codes and what they mean. """

#: A recorded stream failed to delete.
NS_CLEAR_FAILED = 'NetStream.Clear.Failed'

# A recorded stream was deleted successfully.
NS_CLEAR_SUCCESS = 'NetStream.Clear.Success'

#: An attempt to use a Stream method (at client-side) failed.
NS_FAILED = 'NetStream.Failed'

#: Invalid arguments were passed to a NetStream method.
NS_INVALID_ARGUMENT = 'NetStream.InvalidArg'

#: Playlist playback is complete.
NS_PLAY_COMPLETE = 'NetStream.Play.Complete'

#: An attempt to play back a stream failed.
NS_PLAY_FAILED = 'NetStream.Play.Failed'

#: Data is playing behind the normal speed.
NS_PLAY_INSUFFICIENT_BW = 'NetStream.Play.InsufficientBW'

#: Playback was started.
NS_PLAY_START = 'NetStream.Play.Start'

#: An attempt was made to play a stream that does not exist.
NS_PLAY_STREAM_NOT_FOUND = 'NetStream.Play.StreamNotFound'

#: Playback was stopped.
NS_PLAY_STOP = 'NetStream.Play.Stop'

#: A playlist was reset.
NS_PLAY_RESET = 'NetStream.Play.Reset'

#: The initial publish to a stream was successful. This message is sent to
#: all subscribers.
NS_PLAY_PUBLISH_NOTIFY = 'NetStream.Play.PublishNotify'

#: An unpublish from a stream was successful. This message is sent to all
#: subscribers.
NS_PLAY_UNPUBLISH_NOTIFY = 'NetStream.Play.UnpublishNotify'

#: Playlist playback switched from one stream to another.
NS_PLAY_SWITCH = 'NetStream.Play.Switch'

#: Flash Player detected an invalid file structure and will not try to
#: play this type of file.
NS_PLAY_FILE_STRUCTURE_INVALID = 'NetStream.Play.FileStructureInvalid'

#: Flash Player did not detect any supported tracks (video, audio or data)
#: and will not try to play the file.
NS_PLAY_NO_SUPPORTED_TRACK_FOUND = 'NetStream.Play.NoSupportedTrackFound'

#: An attempt was made to publish a stream that is already being published
#: by someone else.
NS_PUBLISH_BAD_NAME = 'NetStream.Publish.BadName'

#: An attempt to publish was successful.
NS_PUBLISH_START = 'NetStream.Publish.Start'

#: An attempt was made to record a read-only stream.
NS_RECORD_NO_ACCESS = 'NetStream.Record.NoAccess'

#: An attempt to record a stream failed.
NS_RECORD_FAILED = 'NetStream.Record.Failed'

#: Recording was started.
NS_RECORD_START = 'NetStream.Record.Start'

#: Recording was stopped.
NS_RECORD_STOP = 'NetStream.Record.Stop'

#: An attempt to unpublish was successful.
NS_UNPUBLISHED_SUCCESS = 'NetStream.Unpublish.Success'

#: The subscriber has used the seek command to move to a particular
#: location in the recorded stream.
NS_SEEK_NOTIFY = 'NetStream.Seek.Notify'

#: The stream doesn't support seeking.
NS_SEEK_FAILED = 'NetStream.Seek.Failed'

#: The subscriber has used the seek command to move to a particular
#: location in the recorded stream.
NS_PAUSE_NOTIFY = 'NetStream.Pause.Notify'

#: Publishing has stopped.
NS_UNPAUSE_NOTIFY = 'NetStream.Unpause.Notify'

#: Unknown
NS_DATA_START = 'NetStream.Data.Start'
