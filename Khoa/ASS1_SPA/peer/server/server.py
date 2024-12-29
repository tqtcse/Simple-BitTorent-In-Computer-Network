import socket
import struct
from threading import Thread
import hashlib
import os
import torrent

# Global map to store workers associated with info hashes
connection_workers = {}

class TorrentFile:
    def __init__(self, announce, info_hash, piece_hashes, piece_length, length, name):
        self.announce = announce
        self.info_hash = info_hash
        self.piece_hashes = piece_hashes
        self.piece_length = piece_length
        self.length = length
        self.name = name

class FileWorker:
    def __init__(self, file_path):
        self.file_path = file_path
        self.pieces = self.load_pieces(file_path)
        self.num_pieces = len(self.pieces)
        self.piece_hashes = self.calculate_piece_hashes(self.pieces)

    def load_pieces(self, file_path):
        with open(file_path, "rb") as f:
            return torrent.split_file_into_pieces(f,256*1024)  

    def calculate_piece_hashes(self, pieces):
        hashes = [hashlib.sha1(piece).digest() for piece in pieces]
        print(hashes)
        return hashes

def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
       s.connect(('8.8.8.8',1))
       ip = s.getsockname()[0]
    except Exception:
       ip = '127.0.0.1'
    finally:
       s.close()
    return ip

def generate_peer_id_with_ip(client_prefix, ip_address):
    peer_id_hash = hashlib.sha1(ip_address.encode()).hexdigest()[:12]  # Get first 12 characters of the hash
    return client_prefix + peer_id_hash

def handle_connection(conn):
    with conn:
        while True:
            message = conn.recv(1024).decode("utf-8").strip()
            if not message:
                break  # Connection closed
            print(f"Received message: {message}")

            if message.startswith("HANDSHAKE:"):
                handle_handshake(conn, message)
                # info_hash, worker = handle_handshake(conn, message)
                # if worker is None:
                #     continue
                # connection_workers[info_hash] = worker

            elif message.startswith("Requesting:"):
                handle_piece_request(conn, message)

            else:
                print(f"Unknown message: {message}")
                conn.sendall(b"ERROR: Unknown message\n")

def new_file_worker(file_path):
    return FileWorker(file_path)

def handle_handshake(conn, message):
    info_hash = message[len("HANDSHAKE:"):]
    found = False
    torrent_files = getTorrentFiles()
    torrent_file_name = ""

    for torrent_file in torrent_files:
        if info_hash == torrent.get_info_hash(torrent_file):
            found = True
            torrent_file_name = torrent_file
            break

    if not found:
        print("This torrent file is not in the list.")
        conn.sendall(b"ERROR: Torrent file not found\n")
        return None

    tfs = torrent.open_torrent(torrent_file_name)
    for tf in tfs:
        filename = f"files/{tf['name']}"
        print(tf['name'])
        worker = new_file_worker(filename)
        connection_workers[tf['info_hash']] = worker
    conn.sendall(b"OK\n")
    print(connection_workers)
    return torrent_file_name, worker

def handle_piece_request(conn, message):
    parts = message.split(":")
    if len(parts) != 3:
        conn.sendall(b"ERROR: Invalid request format\n")
        return

    info_hash = parts[1]
    worker = connection_workers.get(info_hash)
    if not worker:
        conn.sendall(b"ERROR: Handshake required\n")
        return

    piece_index = int(parts[2].strip())
    if piece_index < 0 or piece_index >= worker.num_pieces:
        conn.sendall(b"ERROR: Invalid piece index\n")
        return

    # Send the piece size (8 bytes header) and the actual piece
    piece = worker.pieces[piece_index]
    # print(piece)
    # hash = worker.piece_hashes[piece_index]
    piece_size = len(piece)
    # print(piece_size)
    size_header = struct.pack(">Q", piece_size)  # 8-byte big-endian header
    # print(size_header)
    conn.sendall(size_header)
    conn.sendall(piece)

def getTorrentFiles():
    files = [f for f in os.listdir("torrent_files") if os.path.isfile(os.path.join("torrent_files", f))]
    return files

def start_server(host,port,stop_event):
    print("Thread server listening on: {}:{}".format(host,port))

    serversocket = socket.socket()
    serversocket.bind((host,port))

    serversocket.listen(10)
    while not stop_event.is_set():
        conn, addr = serversocket.accept()
        print(f"Connection from {addr}")
        nconn = Thread(target=handle_connection, args=(conn,))
        nconn.start()



