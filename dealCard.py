import random
import requests
from requests.auth import HTTPBasicAuth
import configparser
from functools import lru_cache
import os
import sys

def get_config_path():
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.join(os.path.dirname(sys.executable), 'RPC.conf')
    else:
        # Running as script
        return os.path.join(os.path.dirname(__file__), 'RPC.conf')

# Read RPC configuration
config = configparser.ConfigParser()
config_path = get_config_path()
if not os.path.exists(config_path):
    raise FileNotFoundError(f"Config file not found: {config_path}")
config.read(config_path)

rpc_user = config['rpcconfig']['rpcuser']
rpc_password = config['rpcconfig']['rpcpassword']
rpc_host = config['rpcconfig']['rpchost']
rpc_port = config['rpcconfig']['rpcport']

# Define the deck of cards
suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace']
deck = [f"{rank} of {suit}" for suit in suits for rank in ranks]

# Define jackpot cards
jackpot_cards = [f"Jackpot of {suit}" for suit in suits]

# Prepare RPC request
url = f"http://{rpc_host}:{rpc_port}"
headers = {'content-type': 'application/json'}
auth = HTTPBasicAuth(rpc_user, rpc_password)

# Use a session for connection pooling
session = requests.Session()
session.auth = HTTPBasicAuth(rpc_user, rpc_password)
session.headers.update({'content-type': 'application/json'})

@lru_cache(maxsize=1)
def get_block_count():
    payload = {
        "method": "getblockcount",
        "params": [],
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = session.post(url, json=payload)
    return response.json()['result']

@lru_cache(maxsize=10000)
def get_block_hash(height):
    payload = {
        "method": "getblockhash",
        "params": [height],
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = session.post(url, json=payload)
    return response.json()['result']

def extract_random_digits(hash_data):
    if len(hash_data) < 3:
        raise ValueError("Hash data too short")
    start = random.randint(0, len(hash_data) - 3)
    return int(hash_data[start:start+3], 16)

def deal_card():
    max_height = get_block_count()
    while True:
        random_height = random.randint(0, max_height)
        block_hash = get_block_hash(random_height)
        
        try:
            digits = extract_random_digits(block_hash)
        except ValueError:
            continue
        
        if 4057 <= digits <= 4060:
            return jackpot_cards[digits - 4057]
        elif digits < 4056:
            return deck[digits % 52]

if __name__ == "__main__":
    result = deal_card()
    if "Jackpot" in result:
        print(f"Congratulations! You hit the {result}!")
    else:
        print(f"Your card is: {result}")
