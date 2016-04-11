import pickle
import os
import files

from defs import REQUEST_SEPARATOR_TOKEN
from utils import log_debug
from network.server import send_data
from network.client import receive_data
from network import client
from files import *


class ZengDaemon(object):

    def __init__(self, zeng_dir, peer_socket, files_db, fileObserver):
        self.dir = zeng_dir
        self.peer_socket = peer_socket
        self.files_db = files_db
        self.fileObserver = fileObserver

        self.downloader = Downloader(zeng_dir, peer_socket, files_db)

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
    def on_get_file_update(self, request):
        self.send_response({"status": "OK"})

        diff = self.fileObserver.compare_files(request.get('files', []))

        if diff and len(diff.import_changes) > 0:
            log_debug("import changes: ", diff.import_changes)

            self.downloader.download_all(diff.import_changes)


    def on_get_file_ls(self):
        files = self.files_db.list()
        self.send_response(files)

    def on_get_file_download(self, zeng_request):
        log_debug("Calling get_file_download")

        local_filename = zeng_request['file']
        file = os.path.join(self.dir, local_filename)
        data = open(file, 'rb').read()

        self.send_response(data)

    def send_response(self, data):
        send_data(self.peer_socket, data)



class ZengClientDaemon(object):

    def __init__(self, shared_dir, peer_socket, files_db, fileObserver):
        self.dir = shared_dir
        self.peer_socket = peer_socket
        # self.files_db = files_db
        self.fileObserver = fileObserver

        self.downloader = Downloader(shared_dir, peer_socket, files_db)

    def handle_event(self, event):
        log_debug("handle_event: ", event)
        if event.type == 'sync':
            self.sync_changes()

    def sync_changes(self):
        changes = self.get_file_changes()

        self.downloader.download_all(changes.import_changes)
        self.post_file_changes(changes.export_changes)

        #TODO: notify local changes to other peer

    def get_file_changes(self):
        log_debug("get_files_list")

        trackedFiles = self.do_request('list')
        diff = self.fileObserver.compare_files(trackedFiles)

        return diff

    def post_file_changes(self, files):
        if files and len(files) > 0:
            self.do_request('update', files=files)

    def do_request(self, req_type, **data_members):
        return client.do_request(self.peer_socket, req_type, **data_members)


class Downloader(object):

    def __init__(self, zeng_dir, peer_socket, files_db):
        self.dir = zeng_dir
        self.peer_socket = peer_socket
        self.files_db = files_db

    def download_all(self, files):
        for f in files:
            self.download_file(f)

    def download_file(self, file):
        log_debug("download: ", file.filename)

        # TODO: correct this
        if file.status == FileStatus.Removed or os.path.exists(file.filename):
            return

        data = client.do_request(self.peer_socket, 'dw', file=file.filename)

        self.save_file(data, file)

    def save_file(self, data, file):
        self.files_db.save(file)

        full_filename = os.path.join(self.dir, file.filename)
        dirs = os.path.dirname(full_filename)

        files.mkdirs(dirs)
        with open(full_filename, 'wb') as output:
            output.write(data)

        #Define o tempo de modificação (e acesso) do arquivo para o timestamp
        # definido em file (ou para o tempo atual)

        times = None
        if file.changed:
            epoch_time = time.mktime(file.changed.timetuple())
            times = (epoch_time, epoch_time)

        os.utime(full_filename, times)
