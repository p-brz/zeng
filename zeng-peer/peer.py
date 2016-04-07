import socket
import sys
import threading

from zeng.defs import ZENG_DEFAULT_PORT
from zeng.network.server import tcp_server_socket, tcp_thread_target

class Peer(object):
    def __init__(self, **kwargs):
        self.dir = kwargs.get('dir')
        self.alias = kwargs.get('alias')
        self.host = kwargs.get('host')

    def start(self):
        if self.host is None:
            self.startAsHost()
        else:
            self.startAsGuest()

    def startAsHost(self):
        server_socket = tcp_server_socket(self.host, ZENG_DEFAULT_PORT)
        tcp_thread_target(server_socket, self.received_connection_handler)

    def received_connection_handler(self, client_socket, client_address):
        # Iniciar DAEMON nesse ponto e usar ele para as operações
        client_socket.close()
        pass

    # #Function for handling connections. This will be used to create threads
    # def clientthread(self, conn, addr):
    #     #Sending message to connected client
    #     conn.sendall(b'Welcome to the server. Type something and hit enter\n') #send only takes string
    #
    #     #infinite loop so that function do not terminate and thread do not end.
    #     while True:
    #
    #         #Receiving from client
    #         data = conn.recv(1024)
    #
    #         print("data: ", data)
    #
    #         reply = bytearray('OK...', 'utf-8')
    #         reply.extend(data)
    #
    #         print("reply: ", reply)
    #
    #         if not data:
    #             break
    #
    #         conn.sendall(reply)
    #
    #     #came out of loop
    #     conn.close()

    def startAsGuest(self):
        pass

    def join(self):
        pass

    def stop(self):
        pass
