from flask import Flask, Response, request
import time
import sqlite3


app = Flask(__name__)

# Initialize SQLite Database
def init_db():
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    # Create the table with PRIMARY KEY constraint on the combination of info_hash and peer_id
    c.execute('''CREATE TABLE IF NOT EXISTS peers (
                    info_hash TEXT,
                    peer_id TEXT,
                    ip TEXT,
                    port INTEGER,
                    downloaded INTEGER,
                    left INTEGER,
                    last_seen REAL,
                    PRIMARY KEY(info_hash, peer_id))''')
    conn.commit()
    conn.close()

# Insert or update peer in the database
def upsert_peer(info_hash, peer_id, ip, port, downloaded, left):
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO peers (info_hash, peer_id, ip, port, downloaded, left, last_seen)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (info_hash, peer_id, ip, port, downloaded, left, time.time()))  # Update with current timestamp
    conn.commit()
    conn.close()

# Get peer list for a specific torrent (info_hash)
def get_peer_list(info_hash):
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    c.execute("SELECT peer_id, ip, port FROM peers WHERE info_hash=?", (info_hash,))
    peers = c.fetchall()
    conn.close()
    return [{"peer_id": peer[0], "ip": peer[1], "port": peer[2]} for peer in peers]

# Function to delete inactive peers based on last_seen
def delete_inactive_peers(inactivity_threshold=3600):
    """
    Delete peers that haven't announced for the given inactivity threshold (in seconds).
    Default is set to 1 hour (3600 seconds).
    """
    current_time = time.time()
    threshold_time = current_time - inactivity_threshold  # Calculate the threshold time

    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()

    # Delete peers where last_seen is older than the threshold
    c.execute("DELETE FROM peers WHERE last_seen < ?", (threshold_time,))
    conn.commit()
    conn.close()

# Announce endpoint for peer communication with the tracker
@app.route('/announce', methods=['GET'])
def announce():
    # Get parameters from the announce request
    info_hash = request.args.get('info_hash')  # Info hash of the torrent
    peer_id = request.args.get('peer_id')  # Peer ID
    peer_ip = request.args.get('peer_ip')
    port = int(request.args.get('port'))  # Peer listening port
    downloaded = int(request.args.get('downloaded'))  # Amount downloaded by the peer
    left = int(request.args.get('left'))  # Amount left to download
    event = request.args.get('event', '')  # Event type: 'started', 'completed', 'stopped'
    compact = request.args.get('compact', '')  # Compact flag for peer list

    # If no info_hash is provided, return error
    if not info_hash:
        return 'Error: Missing info_hash', 400

    # Handle started/completed/stopped events
    if event == 'started' or event == 'completed':
        upsert_peer(info_hash, peer_id, peer_ip, port, downloaded, left)

    elif event == 'stopped':
        conn = sqlite3.connect('tracker.db')
        c = conn.cursor()
        c.execute("DELETE FROM peers WHERE info_hash=? AND peer_id=?", (info_hash, peer_id))
        conn.commit()
        conn.close()

    # Get the peer list for this torrent
    peers = get_peer_list(info_hash)

    # Construct the response as plain text (customized as needed)
    response_data = {
        'info_hash': info_hash,
        'peers': peers  # List of peers
    }

    # Convert the dictionary to a plain-text format (e.g., a string representation)
    response_str = f"info_hash={response_data['info_hash']}\n"
    response_str += "peers="
    response_str += ",".join([f"{peer['ip']}" for peer in peers])
    
    # Return the response with content type as text/plain
    return Response(response_str, content_type='text/plain')

if __name__ == '__main__':
    init_db()  # Initialize the database
    # Start periodic cleanup of inactive peers every 10 minutes (600 seconds)
    import threading
    def periodic_cleanup():
        while True:
            delete_inactive_peers(inactivity_threshold=3600)  # Set threshold to 1 hour (3600 seconds)
            time.sleep(600)  # Run every 10 minutes

    # Start the cleanup process in a separate thread
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()

    # Run Flask app with Gunicorn or Waitress (depending on your choice)
    app.run(debug=True, host='0.0.0.0', port=4000)
