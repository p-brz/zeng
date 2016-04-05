
import socket
import sys
import threading

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

    HOST = ''   # Symbolic name, meaning all available interfaces
    PORT = 8888 # Arbitrary non-privileged port

    def startAsHost(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print ('Socket created')

        #Bind socket to local host and port
        try:
           s.bind((self.HOST, self.PORT))
        except socket.error as msg:
        #    print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            print("error: ", msg)
            sys.exit()

        print('Socket bind complete')

        #Start listening on socket
        s.listen(10)
        print('Socket now listening')

        conn = None
        addr = None
        try:
               #wait to accept a connection - blocking call
               conn, addr = s.accept()
               print('Connected with ' + addr[0] + ':' + str(addr[1]))
        finally:
            print("closing server socket")
            s.close()

        if conn is not None:
            try:
                self.clientthread(conn, addr)
            except:
                conn.close()
                raise

    #Function for handling connections. This will be used to create threads
    def clientthread(self, conn, addr):
        #Sending message to connected client
        conn.sendall(b'Welcome to the server. Type something and hit enter\n') #send only takes string

        #infinite loop so that function do not terminate and thread do not end.
        while True:

            #Receiving from client
            data = conn.recv(1024)

            print("data: ", data)

            reply = bytearray('OK...', 'utf-8')
            reply.extend(data)

            print("reply: ", reply)

            if not data:
                break

            conn.sendall(reply)

        #came out of loop
        conn.close()

    def startAsGuest(self):
        pass

    def join(self):
        pass

    def stop(self):
        pass
