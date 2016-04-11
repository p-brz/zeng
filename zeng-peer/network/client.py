import socket
import pickle


def create_client_socket(target_host, target_port):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((target_host, target_port))

    return client


def receive_data(socket):
    f = socket.makefile('rb', 1024)
    data = pickle.load(f)
    f.close()
    return data
