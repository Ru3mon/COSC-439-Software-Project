import sys
import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox, filedialog
import utils
import os
import subprocess

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
        
        # Conversation management
        self.conversations = {"General": []}  # Track messages per conversation
        self.active_conversation = "General"  # Current active chat
        self.received_files = {}  # Track received files per conversation
        
        # Create received_files directory
        self.files_dir = os.path.join(os.path.dirname(__file__), "received_files")
        os.makedirs(self.files_dir, exist_ok=True)
        
        self.root = tk.Tk()
        self.root.withdraw() # Hide main window initially

        self.login()
        
        if self.running:
            self.root.deiconify() # Show main window
            self.root.title(f"Chat Client - {self.username}")
            self.root.geometry("900x600")
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
        # Define modern color palette
        self.colors = {
            'primary': '#5865F2',
            'private': '#9B59B6',
            'background': '#F8F9FA',
            'sidebar': '#2C2F33',
            'sidebar_hover': '#3A3D42',
            'text_dark': '#23272A',
            'text_light': '#FFFFFF',
            'success': '#43B581',
            'message_bg': '#FFFFFF',
            'active': '#5865F2'
        }
        
        self.root.configure(bg=self.colors['background'])
        
        # Main container
        main_container = tk.Frame(self.root, bg=self.colors['background'])
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Left Sidebar - Conversation List
        self.sidebar = tk.Frame(main_container, bg=self.colors['sidebar'], width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        # Sidebar header
        sidebar_header = tk.Label(
            self.sidebar, 
            text="CONVERSATIONS",
            bg=self.colors['sidebar'],
            fg=self.colors['text_light'],
            font=('Helvetica', 10, 'bold'),
            anchor='w',
            padx=15,
            pady=10
        )
        sidebar_header.pack(fill=tk.X)
        
        # Conversation buttons container
        self.conv_buttons_frame = tk.Frame(self.sidebar, bg=self.colors['sidebar'])
        self.conv_buttons_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        
        # General chat button (always present)
        self.create_conversation_button("General", self.colors['primary'])
        
        # Separator for online users
        separator = tk.Frame(self.sidebar, bg=self.colors['sidebar'], height=2)
        separator.pack(fill=tk.X, pady=10)
        
        online_label = tk.Label(
            self.sidebar,
            text="ONLINE USERS",
            bg=self.colors['sidebar'],
            fg=self.colors['text_light'],
            font=('Helvetica', 9, 'bold'),
            anchor='w',
            padx=15,
            pady=5
        )
        online_label.pack(fill=tk.X)
        
        # User list
        self.user_listbox = tk.Listbox(
            self.sidebar,
            bg=self.colors['sidebar'],
            fg=self.colors['text_light'],
            selectbackground=self.colors['private'],
            font=('Helvetica', 11),
            borderwidth=0,
            highlightthickness=0
        )
        self.user_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.user_listbox.bind('<Double-Button-1>', self.open_private_chat)
        
        # Right side - Chat Area
        self.chat_container = tk.Frame(main_container, bg=self.colors['background'])
        self.chat_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Chat header
        self.chat_header = tk.Frame(self.chat_container, bg=self.colors['primary'], height=60)
        self.chat_header.pack(fill=tk.X)
        self.chat_header.pack_propagate(False)
        
        self.chat_title = tk.Label(
            self.chat_header,
            text="# General Chat",
            bg=self.colors['primary'],
            fg=self.colors['text_light'],
            font=('Helvetica', 16, 'bold'),
            anchor='w',
            padx=20
        )
        self.chat_title.pack(fill=tk.BOTH, expand=True)
        
        # Chat messages area
        chat_frame = tk.Frame(self.chat_container, bg=self.colors['background'])
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.chat_area = scrolledtext.ScrolledText(
            chat_frame,
            state='disabled',
            bg=self.colors['message_bg'],
            fg=self.colors['text_dark'],
            font=('Helvetica', 12),
            borderwidth=0,
            highlightthickness=1,
            highlightbackground='#E0E0E0',
            padx=10,
            pady=10
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for different message types
        self.chat_area.tag_config('system', foreground='#7F8C8D', font=('Helvetica', 11, 'italic'))
        self.chat_area.tag_config('private', foreground=self.colors['private'], font=('Helvetica', 12, 'bold'))
        self.chat_area.tag_config('sent', foreground=self.colors['primary'], font=('Helvetica', 12))
        self.chat_area.tag_config('file', foreground=self.colors['success'], font=('Helvetica', 12, 'bold'))
        
        # Input Area
        self.input_frame = tk.Frame(self.chat_container, bg=self.colors['background'])
        self.input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.msg_entry = tk.Entry(
            self.input_frame,
            font=('Helvetica', 12),
            borderwidth=2,
            relief=tk.SOLID
        )
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.msg_entry.bind("<Return>", self.send_message)
        
        self.send_btn = tk.Button(
            self.input_frame,
            text="Send",
            command=self.send_message,
            bg=self.colors['primary'],
            fg=self.colors['text_light'],
            font=('Helvetica', 11, 'bold'),
            borderwidth=0,
            padx=20,
            cursor='hand2'
        )
        self.send_btn.pack(side=tk.LEFT, padx=(5, 0), ipady=5)
        
        self.file_btn = tk.Button(
            self.input_frame,
            text="📎 File",
            command=self.send_file,
            bg=self.colors['success'],
            fg=self.colors['text_light'],
            font=('Helvetica', 11, 'bold'),
            borderwidth=0,
            padx=15,
            cursor='hand2'
        )
        self.file_btn.pack(side=tk.LEFT, padx=(5, 0), ipady=5)

    def create_conversation_button(self, name, color):
        """Create a conversation button in the sidebar"""
        is_active = (name == self.active_conversation)
        
        btn = tk.Button(
            self.conv_buttons_frame,
            text=f"# {name}" if name == "General" else f"@ {name}",
            bg=color if is_active else self.colors['sidebar'],
            fg=self.colors['text_light'],
            font=('Helvetica', 11, 'bold' if is_active else 'normal'),
            anchor='w',
            borderwidth=0,
            padx=15,
            pady=10,
            cursor='hand2',
            command=lambda: self.switch_conversation(name)
        )
        btn.pack(fill=tk.X, pady=2)
        
        # Hover effects
        if not is_active:
            btn.bind('<Enter>', lambda e: btn.config(bg=self.colors['sidebar_hover']))
            btn.bind('<Leave>', lambda e: btn.config(bg=self.colors['sidebar']))
        
        return btn

    def refresh_conversation_buttons(self):
        """Refresh all conversation buttons to reflect active state"""
        for widget in self.conv_buttons_frame.winfo_children():
            widget.destroy()
        
        # Recreate all conversation buttons
        self.create_conversation_button("General", self.colors['primary'])
        
        for conv_name in self.conversations:
            if conv_name != "General":
                self.create_conversation_button(conv_name, self.colors['private'])

    def switch_conversation(self, conv_name):
        """Switch to a different conversation"""
        self.active_conversation = conv_name
        
        # Update header
        is_private = conv_name != "General"
        header_color = self.colors['private'] if is_private else self.colors['primary']
        header_text = f"@ {conv_name}" if is_private else "# General Chat"
        
        self.chat_header.config(bg=header_color)
        self.chat_title.config(bg=header_color, text=header_text)
        
        # Update file button state
        if is_private:
            # Enable file sending in private chats
            self.file_btn.config(
                bg=self.colors['success'],
                fg=self.colors['text_light'],
                text="📎 Send File",
                state=tk.NORMAL
            )
        else:
            # Disable file sending in general chat
            self.file_btn.config(
                bg='#9E9E9E',
                fg='#CCCCCC',
                text="📎 File (DM only)",
                state=tk.NORMAL  # Keep clickable to show warning
            )
        
        # Refresh conversation buttons
        self.refresh_conversation_buttons()
        
        # Display conversation history
        self.chat_area.config(state='normal')
        self.chat_area.delete(1.0, tk.END)
        
        if conv_name in self.conversations:
            for msg_data in self.conversations[conv_name]:
                self._insert_message(msg_data['text'], msg_data.get('tag'))
        
        self.chat_area.config(state='disabled')

    def open_private_chat(self, event):
        """Open a private chat when double-clicking a user"""
        selection = self.user_listbox.curselection()
        if selection:
            target = self.user_listbox.get(selection[0])
            
            # Create conversation if it doesn't exist
            if target not in self.conversations:
                self.conversations[target] = []
                self.refresh_conversation_buttons()
            
            # Switch to this conversation
            self.switch_conversation(target)

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
                        self.display_message(content, "General", tag='system')
                    elif header == utils.HEADER_PVT:
                        # Parse private message: "[Private from Sender]: Message"
                        # Extract sender from the message
                        if content.startswith("[Private from "):
                            sender_end = content.index("]:")
                            sender = content[14:sender_end]
                            actual_msg = content[sender_end+2:].strip()
                            
                            # Create conversation if needed
                            if sender not in self.conversations:
                                self.conversations[sender] = []
                                self.root.after(0, self.refresh_conversation_buttons)
                            
                            self.display_message(f"{sender}: {actual_msg}", sender, tag='private')
                        else:
                            self.display_message(content, "General", tag='private')
                    elif header == utils.HEADER_FILE:
                        # Format: FILE<SEP>Sender<SEP>Filename<SEP>FileSize
                        sender, filename, filesize = content.split(utils.SEPARATOR)
                        filesize = int(filesize)
                        self.receive_file(sender, filename, filesize)
                    elif header == utils.HEADER_LIST:
                        self.update_user_list(content)
                    elif header == utils.HEADER_ERR:
                        messagebox.showerror("Error", content)
                else:
                    self.display_message(message, "General")

            except OSError:
                break
            except Exception as e:
                print(f"Error receiving: {e}")
                break

    def receive_file(self, sender, filename, filesize):
        """Automatically receive and save files"""
        try:
            # Create sender-specific directory
            sender_dir = os.path.join(self.files_dir, sender)
            os.makedirs(sender_dir, exist_ok=True)
            
            # Save file
            save_path = os.path.join(sender_dir, filename)
            
            # Handle duplicate filenames
            base, ext = os.path.splitext(save_path)
            counter = 1
            while os.path.exists(save_path):
                save_path = f"{base}_{counter}{ext}"
                counter += 1
            
            with open(save_path, 'wb') as f:
                remaining = filesize
                while remaining > 0:
                    chunk_size = min(remaining, utils.BUFFER_SIZE)
                    data = self.sock.recv(chunk_size)
                    if not data:
                        break
                    f.write(data)
                    remaining -= len(data)
            
            # Create conversation if needed
            if sender not in self.conversations:
                self.conversations[sender] = []
                self.root.after(0, self.refresh_conversation_buttons)
            
            # Display clickable file link
            self.display_file_link(sender, filename, save_path, filesize)
            
        except Exception as e:
            print(f"Error receiving file: {e}")
            messagebox.showerror("File Error", f"Failed to receive file: {e}")

    def display_file_link(self, sender, filename, filepath, filesize):
        """Display a clickable file link in the chat"""
        size_kb = filesize / 1024
        size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
        
        msg = f"📎 File received from {sender}: {filename} ({size_str})"
        
        def open_file():
            try:
                subprocess.run(['open', '-R', filepath])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")
        
        # Store file info
        conv = sender
        if conv not in self.conversations:
            self.conversations[conv] = []
        
        # Add to conversation history
        self.conversations[conv].append({
            'text': msg,
            'tag': 'file',
            'filepath': filepath,
            'callback': open_file
        })
        
        # Check if we're already viewing this conversation
        already_in_conversation = (self.active_conversation == conv)
        
        if already_in_conversation:
            # Just display the file link immediately in the current view
            self.root.after(0, lambda: self._insert_clickable_file(msg, open_file))
        else:
            # Show notification and auto-switch to the conversation
            self.root.after(0, lambda: messagebox.showinfo(
                "File Received", 
                f"Received file from {sender}:\n{filename} ({size_str})\n\nClick OK to view the file."
            ))
            
            # Auto-switch to the sender's conversation
            self.root.after(100, lambda: self.switch_conversation(conv))

    def _insert_clickable_file(self, text, callback):
        """Insert a clickable file link into chat area"""
        self.chat_area.config(state='normal')
        
        # Create a unique tag for this file
        tag_name = f"file_{len(self.chat_area.tag_names())}"
        
        self.chat_area.insert(tk.END, text + "\n", (tag_name, 'file'))
        self.chat_area.tag_config(tag_name, underline=True)
        self.chat_area.tag_bind(tag_name, '<Button-1>', lambda e: callback())
        self.chat_area.tag_bind(tag_name, '<Enter>', lambda e: self.chat_area.config(cursor='hand2'))
        self.chat_area.tag_bind(tag_name, '<Leave>', lambda e: self.chat_area.config(cursor=''))
        
        self.chat_area.see(tk.END)
        self.chat_area.config(state='disabled')

    def send_message(self, event=None):
        msg = self.msg_entry.get()
        if msg:
            if self.active_conversation != "General":
                # Send private message
                target = self.active_conversation
                full_msg = f"{target}{utils.SEPARATOR}{msg}"
                utils.send_msg(self.sock, utils.HEADER_PVT, full_msg)
                self.display_message(f"You: {msg}", target, tag='sent')
            else:
                # Broadcast to general
                utils.send_msg(self.sock, utils.HEADER_MSG, msg)
                self.display_message(f"You: {msg}", "General", tag='sent')
            
            self.msg_entry.delete(0, tk.END)

    def send_file(self):
        if self.active_conversation == "General":
            messagebox.showwarning("File Transfer", "Please open a private chat to send a file.")
            return
        
        target = self.active_conversation
        filename = filedialog.askopenfilename(title=f"Select file to send to {target}")
        
        if not filename:
            return
        
        try:
            filesize = os.path.getsize(filename)
            basename = os.path.basename(filename)
            size_kb = filesize / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            
            # Confirmation dialog
            confirm_msg = f"Send this file to {target}?\n\nFile: {basename}\nSize: {size_str}"
            if not messagebox.askyesno("Confirm File Send", confirm_msg):
                return
            
            # Create progress window
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Sending File")
            progress_window.geometry("400x180")
            progress_window.resizable(False, False)
            
            # Use direct color values instead of self.colors to avoid potential issues
            bg_color = '#F8F9FA'
            text_color = '#23272A'
            primary_color = '#5865F2'
            success_color = '#43B581'
            
            progress_window.configure(bg=bg_color)
            
            # Center the progress window
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            # Progress window content
            tk.Label(
                progress_window,
                text=f"Sending file to {target}",
                font=('Helvetica', 13, 'bold'),
                bg=bg_color,
                fg=text_color
            ).pack(pady=(20, 5))
            
            tk.Label(
                progress_window,
                text=f"{basename}",
                font=('Helvetica', 11),
                bg=bg_color,
                fg=text_color
            ).pack(pady=2)
            
            tk.Label(
                progress_window,
                text=f"Size: {size_str}",
                font=('Helvetica', 10),
                bg=bg_color,
                fg='#666666'
            ).pack(pady=2)
            
            status_label = tk.Label(
                progress_window,
                text="Preparing to send...",
                font=('Helvetica', 10, 'bold'),
                bg=bg_color,
                fg=primary_color
            )
            status_label.pack(pady=15)
            
            progress_window.update()
            
            # Send Header: FILE<SEP>Target<SEP>Filename<SEP>FileSize
            header = f"{utils.HEADER_FILE}{utils.SEPARATOR}{target}{utils.SEPARATOR}{basename}{utils.SEPARATOR}{filesize}"
            print(f"[DEBUG] Sending file header: {header}")
            self.sock.send(header.encode(utils.FORMAT))
            
            status_label.config(text="Transferring file data...")
            progress_window.update()
            
            # Wait a bit to ensure server processes header before receiving raw bytes
            import time
            time.sleep(0.2)

            # Send File Data
            print(f"[DEBUG] Sending file content...")
            total_sent = 0
            last_update = 0
            
            with open(filename, 'rb') as f:
                while True:
                    bytes_read = f.read(utils.BUFFER_SIZE)
                    if not bytes_read:
                        break
                    self.sock.send(bytes_read)
                    total_sent += len(bytes_read)
                    
                    # Update progress (throttle updates to avoid UI lag)
                    percentage = int((total_sent / filesize) * 100)
                    if percentage - last_update >= 5 or total_sent == filesize:
                        status_label.config(text=f"Sending... {percentage}%")
                        progress_window.update()
                        last_update = percentage
            
            print(f"[DEBUG] Sent {total_sent} bytes.")
            
            # Show completion
            status_label.config(text="✓ File sent successfully!", fg=success_color)
            progress_window.update()
            time.sleep(1.5)
            
            progress_window.destroy()
            self.display_message(f"📎 Sent file: {basename} ({size_str})", target, tag='file')
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[ERROR] File send failed: {error_details}")
            try:
                progress_window.destroy()
            except:
                pass
            messagebox.showerror("File Transfer Failed", f"Error sending file:\n{str(e)}")

    def display_message(self, message, conversation, tag=None):
        """Add message to conversation history and display if active"""
        if conversation not in self.conversations:
            self.conversations[conversation] = []
        
        self.conversations[conversation].append({'text': message, 'tag': tag})
        
        # Only display if this is the active conversation
        if self.active_conversation == conversation:
            self.root.after(0, lambda: self._insert_message(message, tag))

    def _insert_message(self, message, tag=None):
        """Insert message into chat area"""
        self.chat_area.config(state='normal')
        if tag:
            self.chat_area.insert(tk.END, message + "\n", tag)
        else:
            self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.see(tk.END)
        self.chat_area.config(state='disabled')

    def update_user_list(self, user_str):
        self.root.after(0, lambda: self._update_user_list_impl(user_str))

    def _update_user_list_impl(self, user_str):
        print(f"[DEBUG] Updating user list with: {user_str}")
        users = user_str.split(",")
        self.user_listbox.delete(0, tk.END)
        for user in users:
            if user != self.username:
                self.user_listbox.insert(tk.END, user)

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
