import socket
import utils
import time
import sys

def test_connection():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((utils.HOST, utils.PORT))
        
        # Send username
        sock.send("TestBot".encode(utils.FORMAT))
        
        # Receive welcome/broadcast
        # We expect multiple messages: "TestBot has joined..." and User List
        
        # Give it a second
        time.sleep(1)
        
        # Send a message
        utils.send_msg(sock, utils.HEADER_MSG, "Hello World")
        
        print("Connection and send successful")
        sock.close()
        sys.exit(0)
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()
