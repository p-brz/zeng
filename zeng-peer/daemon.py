import pickle
import os

from defs import REQUEST_SEPARATOR_TOKEN
from utils import log_debug
from network.server import send_data


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
            self.get_file_update(zeng_request)
        elif request_id == 'list':
            self.get_file_ls()
        elif request_id == 'dw':
            self.get_file_download(zeng_request)

    # GET -> Lida com as respostas do par
    def get_file_update(self, filename, timestamp):
        pass

    def get_file_ls(self):
        files = self.files_db.list()
        send_data(self.peer_socket, files)

    def get_file_download(self, zeng_request):
        log_debug("Calling get_file_download")

        local_filename = zeng_request['file']
        file = os.path.join(self.dir, local_filename)
        data = open(file, 'rb').read()

        send_data(self.peer_socket, data)


class ZengClientDaemon(object):

    def __init__(self, zeng_dir, peer_socket, files_db):
        self.dir = zeng_dir
        self.peer_socket = peer_socket
        self.files_db = files_db

    # POST -> Envia mensagens para o par
    def post_file(self, filename):
        pass

    def post_file_ls(self):
        pass

    def post_file_update(self):
        pass
