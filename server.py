import socket
import threading
import utils

class ChatServer:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((utils.HOST, utils.PORT))
        self.server.listen()
        self.clients = {}  # Map username -> socket
        self.addresses = {} # Map socket -> address
        print(f"Server listening on {utils.HOST}:{utils.PORT}")

    def broadcast(self, message, sender_name=None):
        """Send a message to all connected clients."""
        print(f"[DEBUG] Broadcasting: {message} (Sender: {sender_name})")
        for name, client_sock in self.clients.items():
            if name != sender_name:
                try:
                    print(f"[DEBUG] Sending to {name}")
                    utils.send_msg(client_sock, utils.HEADER_MSG, message)
                except Exception as e:
                    print(f"[DEBUG] Error sending to {name}: {e}")
                    self.remove_client(name)

    def handle_client(self, client_sock, address):
        """Handle individual client connection."""
        username = None
        try:
            # First message should be the username
            username = client_sock.recv(utils.BUFFER_SIZE).decode(utils.FORMAT)
            
            if username in self.clients:
                utils.send_msg(client_sock, utils.HEADER_ERR, "Username already taken.")
                client_sock.close()
                return

            self.clients[username] = client_sock
            self.addresses[client_sock] = address
            print(f"New connection: {username} from {address}")
            
            # Notify everyone
            self.broadcast(f"{username} has joined the chat!", "Server")
            self.update_user_list()

            while True:
                message = client_sock.recv(utils.BUFFER_SIZE).decode(utils.FORMAT)
                if not message:
                    break
                
                # Simple parsing
                if message.startswith(utils.HEADER_PVT):
                    # Format: PVT<SEP>TargetUser<SEP>Message
                    _, target, content = message.split(utils.SEPARATOR, 2)
                    self.send_private(target, f"[Private from {username}]: {content}")
                elif message.startswith(utils.HEADER_MSG):
                    # Format: MSG<SEP>Message
                    _, content = message.split(utils.SEPARATOR, 1)
                    self.broadcast(f"{username}: {content}", username)
                elif message.startswith(utils.HEADER_FILE):
                    # Format: FILE<SEP>TargetUser<SEP>Filename<SEP>FileSize
                    try:
                        _, target, filename, filesize = message.split(utils.SEPARATOR)
                        filesize = int(filesize)
                        
                        if target in self.clients:
                            # Forward header to target: FILE<SEP>Sender<SEP>Filename<SEP>FileSize
                            target_sock = self.clients[target]
                            header = f"{utils.HEADER_FILE}{utils.SEPARATOR}{username}{utils.SEPARATOR}{filename}{utils.SEPARATOR}{filesize}"
                            target_sock.send(header.encode(utils.FORMAT))
                            
                            # Relay file data
                            remaining = filesize
                            while remaining > 0:
                                chunk_size = min(remaining, utils.BUFFER_SIZE)
                                data = client_sock.recv(chunk_size)
                                if not data:
                                    break
                                target_sock.send(data)
                                remaining -= len(data)
                            print(f"Relayed file {filename} from {username} to {target}")
                        else:
                            # Consume the file data to clear the buffer if target not found
                            # This prevents the server from interpreting file bytes as commands
                            remaining = filesize
                            while remaining > 0:
                                chunk_size = min(remaining, utils.BUFFER_SIZE)
                                client_sock.recv(chunk_size)
                                remaining -= chunk_size
                            utils.send_msg(client_sock, utils.HEADER_ERR, f"User {target} not found.")

                    except ValueError:
                        print(f"Error parsing file header from {username}")
                else:
                    # Default broadcast
                    self.broadcast(f"{username}: {message}", username)

        except Exception as e:
            print(f"Error handling client {username}: {e}")
        finally:
            if username:
                self.remove_client(username)
                client_sock.close()

    def send_private(self, target_user, message):
        if target_user in self.clients:
            utils.send_msg(self.clients[target_user], utils.HEADER_PVT, message)

    def remove_client(self, username):
        if username in self.clients:
            del self.clients[username]
            self.broadcast(f"{username} has left the chat.", "Server")
            self.update_user_list()

    def update_user_list(self):
        """Send the updated list of users to all clients."""
        users = ",".join(self.clients.keys())
        for client_sock in self.clients.values():
            try:
                utils.send_msg(client_sock, utils.HEADER_LIST, users)
            except:
                pass

    def start(self):
        while True:
            client_sock, address = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(client_sock, address))
            thread.start()

if __name__ == "__main__":
    server = ChatServer()
    server.start()
