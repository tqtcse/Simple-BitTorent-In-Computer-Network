# Simple BitTorent App 
A simple BitTorrent app is an application that implements the core principles of the BitTorrent protocol, allowing users to download and upload files via a decentralized peer-to-peer (P2P) network. The main idea behind BitTorrent is to break large files into smaller pieces and distribute those pieces among multiple peers, which helps speed up file sharing.
# How It Works?

![Use case diagram:](https://github.com/user-attachments/assets/c87e951c-b274-4954-af8a-cc9c63d15844)
![aa](https://github.com/user-attachments/assets/bf8af69b-7c90-4450-8dcc-63f539c7dfad)
# Installation
1. Clone the repository:

`git clone: https://github.com/tqtcse/Simple-BitTorent-In-Computer-Network`
`cd your-repo`

2. Install the required libraries:
`pip install -r requirements.txt`
# How To Run 
1. The first computer is used as a tracker. When run this command, we can see the ip of the http tracker.
   `python app.py`
2. The second computer run as a peer. When run this command, we will see the menu that cotains list of command the app provide. Run the command that the peer want to use
`python peer.py`
# User Command Line Interface
![Interface](https://github.com/user-attachments/assets/29383344-e54c-4d29-b1fd-2bdcbaa83274)
