import base58
import hashlib

def wif_to_hex_private_key(wif):
    # Decode the WIF key
    decoded = base58.b58decode(wif)
    
    # Remove the version byte (first byte) and checksum (last 4 bytes)
    private_key_with_compression_flag = decoded[1:-4]
    
    # Check if it's a compressed private key (33 bytes instead of 32)
    if len(private_key_with_compression_flag) == 33:
        private_key = private_key_with_compression_flag[:-1]  # Remove the compression flag
    else:
        private_key = private_key_with_compression_flag
    
    # Convert to hexadecimal
    hex_private_key = private_key.hex()
    
    return hex_private_key

# Example usage
wif_key = "<wif_key>"  # Example WIF key
hex_key = wif_to_hex_private_key(wif_key)
print(f"WIF Key: {wif_key}")
print(f"Hex Private Key: {hex_key}")
