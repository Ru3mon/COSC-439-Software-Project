import sys
import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox, filedialog
import utils
import os

print(f"Python Version: {sys.version}")
try:
    print(f"Tkinter Version: {tk.TkVersion}")
except:
    print("Tkinter Version: Unknown")


class ChatClient:
    def __init__(self):
        self.sock = None
        self.username = None
        self.running = False
        
        self.root = tk.Tk()
        self.root.withdraw() # Hide main window initially

        self.login()
        
        if self.running:
            self.root.deiconify() # Show main window
            self.root.title(f"Chat Client - {self.username}")
            self.setup_gui()
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
            self.root.mainloop()

    def login(self):
        # Simple dialogs for connection info
        host = simpledialog.askstring("Connect", "Server IP:", initialvalue=utils.HOST)
        port = simpledialog.askinteger("Connect", "Server Port:", initialvalue=utils.PORT)
        self.username = simpledialog.askstring("Login", "Username:")

        if host and port and self.username:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((host, port))
                
                # Send username immediately
                self.sock.send(self.username.encode(utils.FORMAT))
                
                self.running = True
                
                # Start listening thread
                threading.Thread(target=self.receive_messages, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Connection Error", f"Could not connect: {e}")
                self.root.destroy()
        else:
            self.root.destroy()

    def setup_gui(self):
        # Main layout
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Chat Area
        self.chat_area = scrolledtext.ScrolledText(self.main_frame, state='disabled')
        self.chat_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # User List
        self.user_list_frame = tk.Frame(self.main_frame, width=150)
        self.user_list_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        tk.Label(self.user_list_frame, text="Online Users").pack()
        self.user_listbox = tk.Listbox(self.user_list_frame)
        self.user_listbox.pack(fill=tk.BOTH, expand=True)
        self.user_listbox.bind('<Double-Button-1>', self.set_private_target)

        # Input Area
        self.input_frame = tk.Frame(self.root)
        self.input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.msg_entry = tk.Entry(self.input_frame)
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.msg_entry.bind("<Return>", self.send_message)

        self.send_btn = tk.Button(self.input_frame, text="Send", command=self.send_message)
        self.send_btn.pack(side=tk.LEFT, padx=5)

        self.file_btn = tk.Button(self.input_frame, text="Send File", command=self.send_file)
        self.file_btn.pack(side=tk.LEFT)
        
        self.private_target = None # If set, sends private message

    def receive_messages(self):
        while self.running:
            try:
                message = self.sock.recv(utils.BUFFER_SIZE).decode(utils.FORMAT)
                if not message:
                    print("[DEBUG] Connection closed by server")
                    break
                
                print(f"[DEBUG] Received raw: {message}")

                # Check for headers
                if utils.SEPARATOR in message:
                    header, content = message.split(utils.SEPARATOR, 1)
                    
                    if header == utils.HEADER_MSG:
                        self.display_message(content)
                    elif header == utils.HEADER_PVT:
                        self.display_message(f"[PRIVATE] {content}", color="red")
                    elif header == utils.HEADER_FILE:
                        # Format: FILE<SEP>Sender<SEP>Filename<SEP>FileSize
                        _, sender, filename, filesize = content.split(utils.SEPARATOR)
                        filesize = int(filesize)
                        self.receive_file(sender, filename, filesize)
                    elif header == utils.HEADER_LIST:
                        self.update_user_list(content)
                    elif header == utils.HEADER_ERR:
                        messagebox.showerror("Error", content)
                else:
                    self.display_message(message)

            except OSError:
                break
            except Exception as e:
                print(f"Error receiving: {e}")
                break

    def receive_file(self, sender, filename, filesize):
        msg = f"Incoming file from {sender}: {filename} ({filesize} bytes). Save?"
        if messagebox.askyesno("File Transfer", msg):
            save_path = filedialog.asksaveasfilename(initialfile=filename)
            if save_path:
                try:
                    with open(save_path, 'wb') as f:
                        remaining = filesize
                        while remaining > 0:
                            chunk_size = min(remaining, utils.BUFFER_SIZE)
                            data = self.sock.recv(chunk_size)
                            if not data:
                                break
                            f.write(data)
                            remaining -= len(data)
                    self.display_message(f"File saved to {save_path}", color="green")
                except Exception as e:
                    messagebox.showerror("File Error", f"Failed to save file: {e}")
            else:
                 # User cancelled save, but we still need to consume bytes
                 self.consume_bytes(filesize)
        else:
            # User rejected, consume bytes
            self.consume_bytes(filesize)

    def consume_bytes(self, size):
        remaining = size
        while remaining > 0:
            chunk_size = min(remaining, utils.BUFFER_SIZE)
            self.sock.recv(chunk_size)
            remaining -= chunk_size

    def send_message(self, event=None):
        msg = self.msg_entry.get()
        if msg:
            if self.private_target:
                # Send private message
                full_msg = f"{self.private_target}{utils.SEPARATOR}{msg}"
                utils.send_msg(self.sock, utils.HEADER_PVT, full_msg)
                self.display_message(f"[To {self.private_target}]: {msg}", color="blue")
                self.private_target = None # Reset after sending
                self.msg_entry.config(bg="white")
            else:
                # Broadcast
                utils.send_msg(self.sock, utils.HEADER_MSG, msg)
                self.display_message(f"You: {msg}")
            
            self.msg_entry.delete(0, tk.END)

    def send_file(self):
        target = self.private_target
        if not target:
            messagebox.showwarning("File Transfer", "Please double-click a user in the list to send a file privately.")
            return

        filename = filedialog.askopenfilename()
        if filename:
            try:
                filesize = os.path.getsize(filename)
                basename = os.path.basename(filename)
                
                # Send Header: FILE<SEP>Target<SEP>Filename<SEP>FileSize
                header = f"{utils.HEADER_FILE}{utils.SEPARATOR}{target}{utils.SEPARATOR}{basename}{utils.SEPARATOR}{filesize}"
                self.sock.send(header.encode(utils.FORMAT))
                
                # Send File Data
                with open(filename, 'rb') as f:
                    while True:
                        bytes_read = f.read(utils.BUFFER_SIZE)
                        if not bytes_read:
                            break
                        self.sock.send(bytes_read)
                
                self.display_message(f"Sent file {basename} to {target}", color="blue")
                self.private_target = None
                self.msg_entry.config(bg="white")
                
            except Exception as e:
                messagebox.showerror("File Error", f"Failed to send file: {e}")

    def display_message(self, message, color="black"):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.see(tk.END)
        self.chat_area.config(state='disabled')

    def update_user_list(self, user_str):
        users = user_str.split(",")
        self.user_listbox.delete(0, tk.END)
        for user in users:
            if user != self.username:
                self.user_listbox.insert(tk.END, user)

    def set_private_target(self, event):
        selection = self.user_listbox.curselection()
        if selection:
            target = self.user_listbox.get(selection[0])
            self.private_target = target
            self.msg_entry.config(bg="lightyellow")
            messagebox.showinfo("Private Mode", f"Next message will be sent privately to {target}")

    def on_close(self):
        self.running = False
        if self.sock:
            self.sock.close()
        self.root.destroy()

if __name__ == "__main__":
    try:
        ChatClient()
    except Exception as e:
        import traceback
        with open("client_error.log", "w") as f:
            f.write(traceback.format_exc())
        messagebox.showerror("Critical Error", f"Application crashed: {e}\nSee client_error.log")
