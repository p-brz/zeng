from zeng.defs import REQUEST_SEPARATOR_TOKEN


class ZengDaemon(object):

    def __init__(self, my_socket, pair_socket):
        self.my_socket = my_socket
        self.pair_socket = pair_socket

    def listen():
        request = self.pair_socket.recv(1024)
        parsed_request = request.split(REQUEST_SEPARATOR_TOKEN)
        request_id = parsed_request[0]
        if request_id == 'fu':
            self.get_file_update(parsed_request[1], parsed_request[2])
        elif request_id == 'ls':
            self.get_file_ls()
        elif request_id == 'dl':
            self.get_file_download(parsed_request[1])

    # GET -> Lida com as respostas do par
    def get_file_update(filename, timestamp):
        pass

    def get_file_ls():
        pass

    def get_file_download(filename):
        pass

    # POST -> Envia mensagens para o par
    def post_file(filename):
        pass

    def post_file_ls():
        pass

    def post_file_update():
        pass
