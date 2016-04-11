import pickle
import os
import files

from defs import REQUEST_SEPARATOR_TOKEN
from utils import log_debug
from network.server import send_data
from network.client import receive_data
from files import *


class ZengDaemon(object):

    def __init__(self, zeng_dir, peer_socket, files_db):
        self.dir = zeng_dir
        self.peer_socket = peer_socket
        self.files_db = files_db

    def handle_request(self):
        data = self.peer_socket.recv(1024)
        zeng_request = pickle.loads(data)
        request_id = zeng_request['task']

        log_debug("Received message " + str(zeng_request))

        if request_id == 'update':
            self.on_get_file_update(zeng_request)
        elif request_id == 'list':
            self.on_get_file_ls()
        elif request_id == 'dw':
            self.on_get_file_download(zeng_request)

    # GET -> Lida com as respostas do par
    def on_get_file_update(self, filename, timestamp):
        pass

    def on_get_file_ls(self):
        files = self.files_db.list()
        send_data(self.peer_socket, files)

    def on_get_file_download(self, zeng_request):
        log_debug("Calling get_file_download")

        local_filename = zeng_request['file']
        file = os.path.join(self.dir, local_filename)
        data = open(file, 'rb').read()

        send_data(self.peer_socket, data)


class ZengClientDaemon(object):

    def __init__(self, shared_dir, peer_socket, files_db, fileObserver):
        self.dir = shared_dir
        self.peer_socket = peer_socket
        self.files_db = files_db
        self.fileObserver = fileObserver

    def handle_event(self, event):
        log_debug("handle_event: ", event)
        if event.type == 'sync':
            self.sync_changes()

    def sync_changes(self):
        changes = self.get_file_changes()
        self.download_all(changes.import_changes)

    def get_file_changes(self):
        log_debug("get_files_list")

        trackedFiles = self.do_request('list')
        diff = self.fileObserver.compare_files(trackedFiles)

        return diff

    def post_file_update(self):
        pass


    def download_all(self, files):
        for f in files:
            self.download_file(f)

    def download_file(self, file):
        log_debug("download: ", file)

        # TODO: correct this
        if file.status == FileStatus.Removed or os.path.exists(file.filename):
            return

        data = self.do_request('dw', file=file.filename)

        self.save_file(data, file)

    def save_file(self, data, file):
        self.files_db.save(file)

        full_filename = os.path.join(self.dir, file.filename)
        dirs = os.path.dirname(full_filename)

        files.mkdirs(dirs)
        with open(full_filename, 'wb') as output:
            output.write(data)


    def do_request(self, type, **data_members):
        request = {}
        request['task'] = type

        for k in data_members:
            request[k] = data_members[k]

        #send request
        send_data(self.peer_socket, request)

        #receive response
        return receive_data(self.peer_socket) #TODO: implement timeout
