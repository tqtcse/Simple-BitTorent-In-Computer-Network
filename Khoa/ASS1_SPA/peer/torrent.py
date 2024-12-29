import hashlib
import os
import json
import bencodepy
from typing import List
import hashlib
import os
import json
import bencodepy
from typing import List

# New version

# Helper function to split a file into pieces of the given size (256KB)
def split_file_into_pieces(file, piece_length):
    pieces = []
    while True:
        buf = file.read(piece_length)
        if not buf:
            break  # End of file reached
        pieces.append(buf)
    return pieces

# Function to create a torrent from given files and tracker URL
def create_torrent(paths, tracker_url):
    torrent_files = []  # List to store TorrentFile objects
    
    for path in paths:
        piece_length = 256 * 1024  # 256 KB

        filepath = os.path.join("files",path)
        
        # Open the file
        with open(filepath, 'rb') as file:
            file_info = os.stat(filepath)
            pieces = split_file_into_pieces(file, piece_length)
            piece_hashes = [hashlib.sha1(piece).digest() for piece in pieces]
            
            torrent_file = {
                'announce': tracker_url,
                'piece_hashes': piece_hashes,
                'piece_length': piece_length,
                'length': file_info.st_size,
                'name': os.path.basename(path)
            }
            
            torrent_files.append(torrent_file)
    
    return torrent_files

def to_bencode_torrent(torrent_files):
    # Convert the torrent_files list to bencode format
    bto = {
        'announce': torrent_files[0]['announce'],
        'info': []
    }
    for torrent_file in torrent_files:
        bencode_info = {
            'pieces': b''.join(torrent_file['piece_hashes']),
            'piece length': torrent_file['piece_length'],
            'length': torrent_file['length'],
            'name': torrent_file['name']
        }
        bto['info'].append(bencode_info)
    return bto

def save_bencoded_torrent(bto, torrent_file_name):
    with open(os.path.join("torrent_files",torrent_file_name), 'wb') as f:
        f.write(bencodepy.encode(bto))
    print(f"Successfully creating {torrent_file_name}")

def Create(path, tracker_url):
    torrent_files = create_torrent(path, tracker_url)

    # Generate a unique torrent file name using the hash of the combined paths
    if len(path) == 1:
        torrent_file_name = f"{path[0].split('.')[0]}.torrent"
    else:
        combined_path = ",".join(path)
        hash_file_name = hashlib.sha1(combined_path.encode()).hexdigest()
        torrent_file_name = f"{hash_file_name}.torrent"

    # Convert torrent files to bencode format
    bto = to_bencode_torrent(torrent_files)

    # Save the bencoded torrent file
    try:
        save_bencoded_torrent(bto, torrent_file_name)
    except Exception as e:
        return "", str(e)
    
def open_torrent(path):
    filepath = os.path.join("torrent_files",path)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Torrent file not found: {path}")

    try:
        with open(filepath, 'rb') as file:
            torrent_data = bencodepy.decode(file.read())

        torrent_files = to_torrent_file(torrent_data)
        return torrent_files

    except Exception as e:
        print(f"Error reading or decoding torrent file: {e}")
        return []

def to_torrent_file(torrent_data):
    # Extracting necessary information from the bencoded torrent data
    try:
        torrent_files = []
        announce = torrent_data.get(b'announce', b'').decode('utf-8')
        info = torrent_data.get(b'info', {})

        for item in info:
        
            piece_hashes = item.get(b'pieces', [])
            piece_length = item.get(b'piece length', 0)
            length = item.get(b'length', 0)
            name = item.get(b'name', b'').decode('utf-8')

            # Convert piece_hashes to a list of pieces (you might need to decode them if necessary)
            piece_hashes = [piece_hashes[i:i + 20] for i in range(0, len(piece_hashes), 20)]
            info_hash = hashlib.sha1(name.encode()).digest()

            torrent_file = {
                    'announce': announce,
                    'info_hash': info_hash.hex(),
                    'piece_hashes': piece_hashes,
                    'piece_length': piece_length,
                    'length': length,
                    'name': name
            }

            # print(torrent_file)

            torrent_files.append(torrent_file)

        return torrent_files
    
    except Exception as e:
        print(f"Error extracting torrent file data: {e}")
        return []

def stream_file_pieces(file_path, piece_length):
    try:
        with open(file_path, 'rb') as file:
            return split_file_into_pieces(file, piece_length)
    except Exception as e:
        return None, f"Error streaming file pieces: {e}"

# Old version

# Helper function to decode bytes to strings
def decode_bytes(obj):
    """Recursively decode bytes to strings."""
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')  # Decode bytes to string (ignore errors)
    elif isinstance(obj, dict):
        return {decode_bytes(key): decode_bytes(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [decode_bytes(item) for item in obj]
    else:
        return obj
# Function to read the torrent and convert it to JSON format
def read_torrent_as_json(torrent_file_path: str) -> str:
    try:
        # Open the torrent file in binary mode
        with open(torrent_file_path, 'rb') as torrent_file:
            # Decode the torrent file using bencodepy
            torrent_data = bencodepy.decode(torrent_file.read())
        # Decode bytes to strings
        decoded_data = decode_bytes(torrent_data)
        # Convert the decoded data into JSON format (with pretty-printing)
        json_data = json.dumps(decoded_data, indent=4)
        return json_data
    except Exception as e:
        print(f"Error reading or converting torrent file: {e}")
        return ""
    try:
        # Open the torrent file in binary mode
        with open(torrent_file_path, 'rb') as torrent_file:
            # Decode the torrent file using bencodepy
            torrent_data = bencodepy.decode(torrent_file.read())
        
        # Return the decoded data (torrent metadata as a dictionary)
        return torrent_data
    except Exception as e:
        print(f"Error reading torrent file: {e}")
        return None
    
def get_info_hash(torrent_file_path: str) -> str:
    try:
        torrent_file_path = os.path.join("torrent_files",torrent_file_path)
        with open(torrent_file_path, 'rb') as f:
            torrent_data = f.read()
        
        torrent_metadata = bencodepy.decode(torrent_data)
        
        info = torrent_metadata.get(b'info')

        if info is None:
            raise ValueError("The 'info' dictionary was not found in the torrent file.")

        info_bencoded = bencodepy.encode(info)
        info_hash = hashlib.sha1(info_bencoded).digest()

        return info_hash.hex()

    except Exception as e:
        print(f"Error reading torrent file: {e}")
        return None
    
def get_total_length_from_torrent(torrent_file):
    # Read the .torrent file
    torrent_file = os.path.join("torrent_files",torrent_file)
    with open(torrent_file, 'rb') as f:
        torrent_data = bencodepy.decode(f.read())

    # Get the 'files' list inside the 'info' dictionary
    files = torrent_data[b'info'][b'files']
    
    # Sum the 'length' of each file to get the total size in bytes
    total_length = sum(file[b'length'] for file in files)

    print(total_length)
    
    return total_length

def merge_pieces(output_path, pieces, piece_hashes):
        try:
            # Create or open the output file
            with open(f"files/{output_path}", "wb") as file:
                # Write pieces in order
                for i in range(len(piece_hashes)):
                    if i not in pieces:
                        raise ValueError(f"Missing piece {i}")
                    data = pieces[i]
                    file.write(data)
            return None  # Return None if successful
        except Exception as e:
            return f"Error: {e}"

def parse_torrent_file(filename):
    try:
        # Open the torrent file in binary mode
        with open(f"torrent_files/{filename}", "rb") as f:
            encoded_torrent = f.read()
        
        # Decode the torrent file
        torrent_data = bencodepy.decode(encoded_torrent)
        
        # Extract the necessary information
        announce_url = torrent_data.get(b'announce', b'').decode('utf-8')
        info = torrent_data.get(b'info', {})
        name = info.get(b'name', b'').decode('utf-8')
        piece_length = info.get(b'piece length', 0)
        pieces = info.get(b'pieces', b'')
        files = []

        # Parse pieces into piece_hashes (list of SHA1 hashes)
        piece_hashes = [pieces[i:i+20] for i in range(0, len(pieces), 20)]

        # If there are multiple files, extract their information
        if b'files' in info:
            for file in info[b'files']:
                length = file.get(b'length', 0)
                path = b'/'.join(file.get(b'path', [])).decode('utf-8')
                files.append({'length': length, 'path': path})
        else:
            # Single file mode
            length = info.get(b'length', 0)
            files.append({'length': length, 'path': name})
        
        # Return parsed information, including piece_hashes
        return {
            'announce': announce_url,
            'name': name,
            'piece_length': piece_length,
            'pieces': piece_hashes,  # This will be a list of 20-byte piece hashes
            'files': files
        }

    except Exception as e:
        print(f"Error parsing torrent file: {e}")
        return None
    
# open_torrent("e473c24916f7e86e90d7774af6a730409d2d20f5.torrent")