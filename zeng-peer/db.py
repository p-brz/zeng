
import model
from TrackedFile import *

import time

from sqlalchemy import orm

class FilesDb(object):
    def __init__(self, **kwargs):
        self.dbfile = kwargs.get('dbfile', '.zeng.sqlite')

        from sqlalchemy import create_engine
        self.engine = create_engine('sqlite:///' + self.dbfile, connect_args={'check_same_thread':False})

        from sqlalchemy.orm import sessionmaker
        FilesDb.Session = orm.scoping.scoped_session(sessionmaker())
        FilesDb.Session.configure(bind=self.engine)

    def create(self):
        model.Model.metadata.create_all(self.engine)

    def makeSession(self, dbSession=None):
        return dbSession if dbSession is not None else FilesDb.Session()

    def get(self, dbSession=None, **kwargs):
        s = self.makeSession(dbSession)

        filename = kwargs.get('filename')

        return s.query(TrackedFile).filter(TrackedFile.filename == filename).one_or_none()

    def list(self, dbSession=None):
        s = self.makeSession(dbSession)

        return s.query(TrackedFile).all()

    def listByName(self):
        return TrackedFile.index_by_name(self.list())

    def save(self, file, dbSession=None, autocommit=True):
        s = self.makeSession(dbSession)

        s.merge(file)

        if autocommit:
            s.commit()

    def saveAll(self, files, dbSession=None):
        s = self.makeSession(dbSession)

        for f in files:
            self.save(f, s, False)

        s.commit()

def main():
    filesDb = FilesDb()
    filesDb.create()

    print ("files: ", filesDb.list())

    # file = TrackedFile('zeeng-peer/db.py')
    # file.status = FileStatus.Synced
    files = [
        TrackedFile('zeng-peer/db.py', status=FileStatus.Synced)
        , TrackedFile('README.md', status=FileStatus.Removed)
    ]
    filesDb.saveAll(files)

    print ("files: ", filesDb.list())
    print ("files by name: ", filesDb.listByName())

if __name__ == "__main__":
    main()
