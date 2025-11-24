import socket

# Network Constants
HOST = '0.0.0.0'  # Listen on all available interfaces
PORT = 55556
BUFFER_SIZE = 1024
FORMAT = 'utf-8'

# Protocol Constants
SEPARATOR = "<SEP>"
HEADER_MSG = "MSG"
HEADER_PVT = "PVT"
HEADER_FILE = "FILE"
HEADER_LIST = "LIST"
HEADER_ERR = "ERR"

def send_msg(sock, header, content):
    """Helper to send a formatted message."""
    try:
        msg = f"{header}{SEPARATOR}{content}"
        sock.send(msg.encode(FORMAT))
    except Exception as e:
        print(f"Error sending message: {e}")
