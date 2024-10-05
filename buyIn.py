import configparser
from bitcoinrpc.authproxy import AuthServiceProxy

# Load RPC credentials from RPC.conf
config = configparser.ConfigParser()
config.read('RPC.conf')

rpc_user = config['rpcconfig']['rpcuser']
rpc_password = config['rpcconfig']['rpcpassword']
rpc_host = config['rpcconfig']['rpchost']
rpc_port = config['rpcconfig']['rpcport']

# Create a connection to the luckycoin RPC server
rpc_connection = AuthServiceProxy(f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}")

# Define the recipient address
recipient_address = "<Pool Address>"

# Create and send the transaction
def send_lucky(sending_address, recipient_address, amount):
    # Get UTXOs for the sending address
    utxos = rpc_connection.listunspent(1, 9999999, [sending_address])
    
    if not utxos:
        print("No UTXOs available to spend from the sending address.")
        return None

    # Calculate the total amount of UTXOs
    total_amount = sum(utxo['amount'] for utxo in utxos)

    if total_amount < amount:
        print("Insufficient funds in the sending address.")
        return None

    # Create a transaction using only UTXOs from the sending address
    txid = rpc_connection.sendtoaddress(recipient_address, amount, "", "", False)
    print(f"Transaction sent with txid: {txid}")
    return txid

# Example usage
if __name__ == "__main__":
    sending_address = "<player address>"  # Define sending address here
    amount_to_send = 1  # Amount in lucky
    result_txid = send_lucky(sending_address, recipient_address, amount_to_send)
    if result_txid:
        print(f"Transaction successful. TXID: {result_txid}")
    else:
        print("Transaction failed.")