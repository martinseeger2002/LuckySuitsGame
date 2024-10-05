import json
from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import configparser

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_rpc_connection():
    config = configparser.ConfigParser()
    config.read('RPC.conf')
    rpc_user = config['rpcconfig']['rpcuser']
    rpc_password = config['rpcconfig']['rpcpassword']
    rpc_host = config['rpcconfig']['rpchost']
    rpc_port = config['rpcconfig']['rpcport']
    rpc_url = f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}"
    return AuthServiceProxy(rpc_url)

def import_address(address):
    rpc_connection = get_rpc_connection()
    try:
        rpc_connection.importaddress(address, "", False)
    except JSONRPCException as e:
        print(f"Error importing address {address}: {e}")

def get_address_info(address):
    rpc_connection = get_rpc_connection()
    try:
        utxos = rpc_connection.listunspent(0, 9999999, [address])
        
        balance = sum(Decimal(utxo['amount']) for utxo in utxos)
        
        formatted_utxos = [
            {
                'txid': utxo['txid'],
                'vout': utxo['vout'],
                'amount': Decimal(utxo['amount']),
                'confirmations': utxo['confirmations']
            }
            for utxo in utxos
        ]
        
        # Sort UTXOs by confirmations (descending) and amount (descending)
        formatted_utxos.sort(key=lambda x: (-x['confirmations'], -x['amount']))
        
        return balance, formatted_utxos
    except JSONRPCException as e:
        print(f"Error fetching data for {address}: {e}")
        return None, None

def get_balances_and_utxos(player_wallet, player_pool_wallet):
    player_balance, player_utxos = get_address_info(player_wallet)
    pool_balance, pool_utxos = get_address_info(player_pool_wallet)
    
    result = {
        "player_wallet": {
            "address": player_wallet,
            "balance": float(player_balance) if player_balance is not None else None,
            "utxos": player_utxos if player_utxos is not None else []
        },
        "player_pool_wallet": {
            "address": player_pool_wallet,
            "balance": float(pool_balance) if pool_balance is not None else None,
            "utxos": pool_utxos if pool_utxos is not None else []
        }
    }
    
    return result

def filter_utxos(wallet):
    wallet['utxos'] = [utxo for utxo in wallet['utxos'] if utxo['amount'] != Decimal('0.001')]
    return wallet

# Modify the get_filtered_balances_and_utxos function
def get_filtered_balances_and_utxos(player_wallet, player_pool_wallet):
    # Import addresses as watch-only without rescanning
    import_address(player_pool_wallet)
    
    result = get_balances_and_utxos(player_wallet, player_pool_wallet)
    
    # Filter out 0.001 UTXOs
    result['player_wallet'] = filter_utxos(result['player_wallet'])
    result['player_pool_wallet'] = filter_utxos(result['player_pool_wallet'])
    
    return result

# Example usage
if __name__ == "__main__":
    player_wallet = "<Player Address>"
    player_pool_wallet = "<Pool Address>"
    
    result = get_filtered_balances_and_utxos(player_wallet, player_pool_wallet)
    
    print(json.dumps(result, indent=2, cls=DecimalEncoder))