import socket
import struct
import threading
import hashlib
import json
import time
import bencodepy
import torrent
import requests

connected_tracker_addresses = []

class AddrAndFilename:
    def __init__(self, addr, filename):
        self.addr = addr
        self.filename = filename

class PieceWork:
    def __init__(self, index, hash, size):
        self.index = index
        self.hash = hash
        self.size = size

class PieceResult:
    def __init__(self, index, data, error):
        self.index = index
        self.data = data
        self.error = error

def download_worker(peer, work_queue, results, info_hash):
    while work_queue:
        piece = work_queue.pop(0)
        print(f"Downloading piece {piece.index} from peer {peer}")
        data, error = request_piece_from_peer(peer, piece.index, info_hash)
        results.append(PieceResult(piece.index, data, error))

def request_piece_from_peer(address, piece_index, info_hash):
    try:
        with socket.create_connection((address, 8080), timeout=60) as conn:
            # perform_handshake(address, info_hash)
            message = f"Requesting:{info_hash}:{piece_index}\n".encode()
            conn.sendall(message)

            size_header = conn.recv(8)
            print(f"size_header:{size_header}")

            piece_size = struct.unpack(">Q", size_header)[0]
            # print(piece_size)
            data = receive_exactly(conn,piece_size)
            # print(data)
            return data, None
    except Exception as e:
        return None, str(e)

def receive_exactly(conn, size):
    data = b""
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise Exception("Connection closed prematurely")
        data += chunk
    return data


def test_connection(address):
    try:
        with socket.create_connection((address.split(":")[0], int(address.split(":")[1])), timeout=5) as conn:
            conn.sendall(b"test:\n")
            response = conn.recv(1024).decode()
            print(f"Received response: {response}")
            return True
    except Exception as e:
        print(f"Test connection failed: {e}")
        return False

    # def perform_handshake(address, info_hash):
    # try:
    #     with socket.create_connection((address.split(":")[0], int(address.split(":")[1])), timeout=5) as conn:
    #         handshake_msg = f"HANDSHAKE:{info_hash.hex()}\n".encode()
    #         conn.sendall(handshake_msg)
    #         response = conn.recv(1024).decode()
    #         return response.strip() == "OK"
    # except Exception as e:
    #     print(f"Handshake failed: {e}")
    #     return False
    
def AnnounceToTracker( peer_address, filename):
    try:
        torrent_info = torrent.parse_torrent_file(filename)

        tracker_url = torrent_info['announce']
        filename = torrent_info['name']

        print(tracker_url)

        connect_to_tracker(tracker_url, peer_address, filename)

        exist = any(
                    tracker["address"] == tracker_url and tracker["filename"] == filename 
                    for tracker in connected_tracker_addresses
                )
        if not exist:
                connected_tracker_addresses.append({
                    "address": tracker_url,
                    "filename": filename
                })
                print(f"Tracker {tracker_url} added for file {filename}")
        else:
                print("Already connected to this tracker for this file")
    except Exception as e:
        print(f"Failed to announce to tracker: {e}")
    # try:
    #     with open(f"torrent_files/{filename}", "r") as f:
    #     #     torrent_files = json.load(f)
        
    #     # for tf in torrent_files:
    #     #     tracker_address = tf["announce"]
    #         # filename = tf["FileName"]
    #         bencoded_data = f.read()
    #         tracker_address = bencodepy.decode(bencoded_data)
    #         print(tracker_address)
            # print(filename)
            # connect_to_tracker(tracker_address, peer_address, filename)
            
            # exist = any(
            #     tracker["Addr"] == tracker_address and tracker["Filename"] == filename 
            #     for tracker in connected_tracker_addresses
            # )
            
            # if not exist:
            #     connected_tracker_addresses.append({
            #         "Addr": tracker_address,
            #         "Filename": filename
            #     })
            #     print(f"Tracker {tracker_address} added for file {filename}")
            # else:
            #     print("Already connected to this tracker for this file")
    # except Exception as e:
    #     print(f"Failed to announce to tracker: {e}")

def connect_to_tracker(tracker_address, peer_address, filename):
    try:
        with socket.create_connection((tracker_address.split(":")[0], int(tracker_address.split(":")[1]))) as conn:
            message = f"START:{peer_address}:{filename}\n".encode()
            conn.sendall(message)
            print(f"Connected to tracker {tracker_address} for file {filename}")
    except Exception as e:
        print(f"Connection to tracker failed: {e}")

def Seed(peer_id, peer_address, filename ):
    try:
        seedToTracker(peer_id, peer_address, filename)

        # exist = any(
        #             tracker["address"] == tracker_url and tracker["filename"] == filename 
        #             for tracker in connected_tracker_addresses
        #         )
        # if not exist:
        #         connected_tracker_addresses.append({
        #             "address": tracker_url,
        #             "filename": filename
        #         })
        #         print(f"Tracker {tracker_url} added for file {filename}")
        # else:
                # print("Already connected to this tracker for this file")
    except Exception as e:
        print(f"Failed to announce to tracker: {e}")

def seedToTracker(peer_id, peer_ip, filename):
    torrents = torrent.open_torrent(filename)
    tracker_url = torrents[0]['announce']
    info_hash = torrent.get_info_hash(filename)
    total_length = sum(torrent['length'] for torrent in torrents)

    tracker_request(
                tracker_url=tracker_url,
                info_hash=info_hash,
                peer_id=peer_id,
                peer_ip=peer_ip,
                downloaded=total_length,
                event="completed"
            )

def Download(peer_id, peer_ip, torrentfile):
    try:
        torrents = torrent.open_torrent(torrentfile)
        print(torrents)
        tracker_url = torrents[0]['announce']

        info_hash = torrent.get_info_hash(torrentfile)
        total_length = sum(torrent['length'] for torrent in torrents)
        remain = total_length

        tracker_response = tracker_request(tracker_url=tracker_url,
                                           info_hash=info_hash,
                                           peer_id=peer_id,
                                           peer_ip=peer_ip,
                                           left=total_length
                                       )
        
        # The peers list
        peers = getPeerList(tracker_response)
        peers.remove(peer_ip)   #Except my own peer IP

        active_peers = handshake_peers_multithread(peers,info_hash)

        if len(active_peers) == 0:
            print(f"No active peer!!!")
            return
        
        print(active_peers)

        # Downloading stage
        for tf in torrents:
            print(f"Downloading file: {tf['name']}")

            num_workers = 7
            work_queue = []
            results = []

            # Enqueue work for current file
            for i, hash in enumerate(tf['piece_hashes']):
                work_queue.append(PieceWork(i, hash, tf['piece_length']))

            threads = []
            for i in range(num_workers):
                peer_index = i % len(active_peers)
                thread = threading.Thread(target=download_worker, args=(active_peers[peer_index], work_queue, results, tf['info_hash']))
                thread.start()
                threads.append(thread)

            # Wait for all threads to finish
            for thread in threads:
                thread.join()

            # Process results
            pieces_by_index = {}
            for result in results:
                if result.error:
                    print(f"Error downloading piece {result.index}: {result.error}")
                    continue
                pieces_by_index[result.index] = result.data

                calculated_hash = hashlib.sha1(result.data).digest()
                if calculated_hash != tf['piece_hashes'][result.index]:
                    print(f"Piece {result.index} hash mismatch!")
                else:
                    print(f"Successfully downloaded piece {result.index} of {tf['name']}")

            # Merge pieces
            try:
                torrent.merge_pieces(tf['name'], pieces_by_index, tf["piece_hashes"]) 
            except Exception as e:
                print(f"Error merging pieces for {tf['name']}: {e}")

            print(f"Download complete for file: {tf['name']}")

            remain = remain - tf['length']

            
            tracker_request(
                tracker_url=tracker_url,
                info_hash=info_hash,
                peer_id=peer_id,
                peer_ip=peer_ip,
                downloaded=total_length-remain,
                left=remain,
                event="completed" if remain == 0 else "started"
            )
        
        # Connect to tracker and send data
        # try:
        #     # connect_to_trackertorrent_info['announce'], peer_address, torrent_info['name'])
        # except Exception as e:
        #     print(f"Failed to connect to tracker: {e}")
        

        
    except Exception as e:
        print(f"DOWNLOAD: Failed to announce to tracker: {e}")

def test_connection(address):
    try:
        # Set timeout for the entire operation
        conn = socket.create_connection((address, 8080), timeout=5)  # Assuming the port 6881, change if needed
    except socket.error as e:
        return f"Connection failed: {e}"
    
    try:
        conn.settimeout(5)

        message = b"test:\n"
        conn.sendall(message)

        response = conn.recv(1024)  
        print(f"Received response: {response.decode()}")

    except socket.error as e:
        return f"Failed to send test message or read response: {e}"
    
    finally:
        conn.close()

    return "Connection and message exchange successful."

def perform_handshake(address,info_hash):
    try:
        conn = socket.create_connection((address, 8080), timeout=5)  
        handshake_msg = f"HANDSHAKE:{info_hash}\n"  
        conn.sendall(handshake_msg.encode())  
        response = conn.recv(1024).decode().strip() 
        if response == "OK":
            print("Handshake successful!")
        else:
            print(f"Invalid handshake response: {response}")
            return False
    except socket.timeout:
        print("Connection timeout.")
        return False
    except Exception as e:
        print(f"Error during handshake: {e}")
        return False
    finally:
        conn.close()
    return True

def receive_exactly(conn, size):
    data = b""
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise Exception("Connection closed prematurely")
        data += chunk
    return data


def get_active_peer(address,info_hash,active_peers,lock):
    thread_id = threading.get_ident() 
    if perform_handshake(address,info_hash):
        with lock:
            active_peers.append(address)
            print(f"Thread {thread_id}: Added {address} to active peers")

def handshake_peers_multithread(peers,info_hash):
    active_peers = []
    lock = threading.Lock()

    threads = []
    for peer in peers:
        thread = threading.Thread(target=get_active_peer,args=(peer,info_hash,active_peers,lock))
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print(f"Active peers after handshake: {active_peers}")
    return active_peers

def getPeerList(response: str):
    peers_line = next(line for line in response.splitlines() if line.startswith('peers='))
    peers = peers_line[len("peers="):].split(',')
    print(peers)
    return peers

def tracker_request(tracker_url, info_hash, peer_id, peer_ip, port=8080, downloaded=0, left=0, event="started"):
    params = {
        'info_hash': info_hash,
        'peer_id': peer_id,
        'peer_ip': peer_ip,
        'port': port,
        'downloaded': downloaded,
        'left': left,
        'compact': 0,  
        'event': event  
    }

    response = requests.get(f"{tracker_url}/announce", params=params)

    if response.status_code == 200:
        print("Tracker response:")
        print(response.text)  
        return response.text
    else:
        print(f"Failed to connect to tracker. Status code: {response.status_code}")
        return None
    
def disconnect_to_tracker(peer_id,peer_ip):
    if len(connected_tracker_addresses) == 0:
        print("No connected trackers")
        return
    for tracker in connected_tracker_addresses:
        tracker_request(
                tracker_url=tracker,
                info_hash='',
                peer_id=peer_id,
                peer_ip=peer_ip,
                event="stopped"
            )
