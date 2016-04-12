import time
from datetime import datetime
from os import path

import model
import sqlalchemy
from sqlalchemy import Column


class TrackedFile(model.Model):
    __tablename__ = 'files'

    filename = Column(sqlalchemy.String(150), primary_key=True)
    changed = Column(sqlalchemy.DateTime)
    status = Column(sqlalchemy.Integer)
    is_dir = Column(sqlalchemy.Boolean)

    def __init__(self, *args, **kwargs):
        super(TrackedFile, self).__init__()

        self.changed = kwargs.get('changed', None)
        self.status = kwargs.get('status', FileStatus.Unknown)
        self.is_dir = kwargs.get('is_dir', None)

        default_filename = args[0] if len(args) > 0 else None
        self.filename = kwargs.get('filename', default_filename)

        base_dir = kwargs.get('base_dir', None)
        if base_dir:
            self.filename = TrackedFile.relative_filename(self.filename,
                                                          base_dir)

        if self.exists():
            if not self.changed:
                self.changed = datetime.fromtimestamp(path.getmtime(self.filename))

            if self.is_dir is None:
                self.is_dir = path.isdir(self.filename)

    def isHidden(self):
        if not self.filename:
            return False

        basename = path.basename(self.filename)
        return self.filename.startswith(".") or basename.startswith(".")

    def clone(self):
        cloned = TrackedFile()
        cloned.changed = self.changed
        cloned.filename = self.filename
        cloned.status = self.status
        return cloned

    def exists(self):
        return self.filename is not None and path.exists(self.filename)

    def __repr__(self):
        return "".join([
            "<file: ", str(self.filename),
            "; changed: ", str(self.changed),
            "; status: ", FileStatus.to_string(self.status),
            "; is_dir: ", str(self.is_dir),
            ">"])

    @staticmethod
    def relative_filename(filename, base_dir):
        realPath = path.realpath(filename)
        return path.relpath(realPath, base_dir)

    @staticmethod
    def index_by_name(files):
        filesByName = {}

        for f in files:
            filesByName[f.filename] = f

        return filesByName


class FileStatus(object):
    Unknown = 0
    Unsynced = 1  # new or changed
    Synced = 2
    Removed = 3

    @staticmethod
    def to_string(status):
        Class = FileStatus

        if status == Class.Unsynced:
            return "Unsynced"
        if status == Class.Synced:
            return "Synced"
        if status == Class.Removed:
            return "Removed"
        else:
            return "Unknown"
