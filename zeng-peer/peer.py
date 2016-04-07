
import socket
import sys
import threading
import select

import queue
from queue import Queue

from db import FilesDb
from files import FileObserver

import network
from network import server
import defs
# from zeng.network import server

class Peer(object):
    HOST = ''   # Symbolic name, meaning all available interfaces
    PORT = 8888 # Arbitrary non-privileged port

    def __init__(self, **kwargs):
        self.dir = kwargs.get('dir')
        self.alias = kwargs.get('alias')
        self.host = kwargs.get('host')

        self.event_queue = Queue()

        self.fileObserver = FileObserver(self.dir, FilesDb())

        self.running = False

    def start(self):
        if self.host is None:
            self.startAsHost()
        else:
            self.startAsGuest()

    #def startAsHost(self):
    #    conn, addr = self._wait_guest_connect()
    #    self.run(conn, addr)

    def startAsGuest(self):
        pass

    def startAsHost(self):
        server_socket = None
        try:
            server_socket = server.tcp_server_socket('', defs.ZENG_DEFAULT_PORT)
            # tcp_thread_target(server_socket, self.received_connection_handler)
            client_socket, client_address = server_socket.accept()
            self.received_connection_handler(client_socket, client_address)

        finally:
            print("closing server socket")
            if server_socket:
                server_socket.close()


    def received_connection_handler(self, client_socket, client_address):
        self.running = True

        if client_socket is None:
            return

        self.startFileObserver()

        try:
            self._process_messages(client_socket)
        except:
            raise #relança exceção
        finally:
            #ensure that connection is closed
            client_socket.close()

    def stop(self):
        print("stop!")
        self.fileObserver.stop()
        self._clear_queue()
        self.running = False

    def _clear_queue(self):
        try:
            while True: #read until get exception (queue empty)
                self.event_queue.get_nowait()
                self.event_queue.task_done()
        except queue.Empty:
            pass

    def join(self):
        print("join!")
        self.fileObserver.join()
        print("joined file observer")
        self.event_queue.join()
        print("finish join")


    def startFileObserver(self):
        #Verify and save local changes
        changes = self.fileObserver.check_changes()
        self.fileObserver.saveAllChanges(changes)

        #begin monitor file changes
        self.fileObserver.monitor_changes(self)

    def onNewFile(self, file):
        self.event_queue.put(file)

    def onFileChange(self, file):
        self.event_queue.put(file)

    def onFileRemoved(self, file):
        self.event_queue.put(file)

    def _process_messages(self, peer_socket):
        while self.running:
            ready_sockets = []

            # Bloqueia até tempo de timeout ou detectar que há conteúdo a ser lido em peer_socket
            ready_sockets, _, _ = select.select([peer_socket], [], [], defs.POLL_TIME)

            # Se lista não está vazia, então há uma requisição
            if len(ready_sockets) > 0:
                self._handle_request(peer_socket)
            else:
                # Caso contrário (timeout), tenta processar fila de eventos
                self._process_queue()

        print("finish processing messages")

    def _handle_request(self, conn):
        data = conn.recv(1024)
        zeng_request = pickle.loads(data)

        if zeng_request['task'] == 'dw':
            self._handle_download_request(conn, zeng_request)

        # #Create bytearray to send response
        # reply = bytearray('OK...', 'utf-8')
        # reply.extend(data)
        #
        # print("reply: ", reply)
        #
        # if not data:
        #     return
        #
        # conn.sendall(reply)

    def _handle_download_request(self, conn, zeng_request):
        local_filename = zeng_request['file']
        file = os.path.join(self.dir, filename)
        f = open(file, 'rb')
        serialized = pickle.dump(f.read())
        conn.sendall(serialized)


    def _receive_file(self, filename, conn):
        f = open(filename, 'wb')
        data = socket.recv(1024)
        while data:
            f.write(data)
            data = socket.recv(1024)

        f.close()

    def _process_queue(self):
        try:
            #Loop infinito - será interrompido quando lista estiver vazia (exceção é lançada)
            while True:
                item = self.event_queue.get_nowait()

                #TODO: tratar item obtido da fila
                print("Got queue item: ", item)

                self.event_queue.task_done()
        except queue.Empty:
            pass

    def _wait_guest_connect(self):
        s = self._create_server_socket()

        conn = None
        addr = None
        try:
               #wait to accept a connection - blocking call
               conn, addr = s.accept()
               print('Connected with ' + addr[0] + ':' + str(addr[1]))
        finally:
            print("closing server socket")
            s.close()

        return (conn, addr)
