from os import path

import time

class FileStatus(object):
    Unknown=0
    Unsynced=1 #new or changed
    Synced=2
    Removed=3

    @staticmethod
    def to_string(status):
        Class = FileStatus

        if status == Class.Unsynced : return "Unsynced"
        if status == Class.Synced   : return "Synced"
        if status == Class.Removed  : return "Removed"
        else                        : return "Unknown"

class TrackedFile(object):

    def __init__(self, *args, **kwargs):
        self.changed  = kwargs.get('changed', None)
        self.status   = kwargs.get('status', FileStatus.Unknown)

        default_filename = args[0] if len(args) > 0 else None
        self.filename = kwargs.get('filename', default_filename)

        base_dir = kwargs.get('base_dir', None)
        if base_dir:
           self.filename = TrackedFile.relative_filename(self.filename, base_dir)

        if not self.changed and self.exists():
            self.changed = path.getmtime(self.filename)

    def clone(self):
        cloned = TrackedFile()
        cloned.changed  = self.changed
        cloned.filename = self.filename
        cloned.status   = self.status
        return cloned

    def exists(self):
        return self.filename is not None and path.exists(self.filename)


    def __repr__(self):
        return "".join([
                "<file: ", str(self.filename)
                , "; changed: ", time.asctime(time.gmtime(self.changed))
                , "; status: " , FileStatus.to_string(self.status)
                ,">"])

    @staticmethod
    def relative_filename(filename, base_dir):
        realPath = path.realpath(filename)
        return path.relpath(realPath, base_dir)
