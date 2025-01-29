import os
import binascii

def generate_swarm_key():
  """
  Generate a 32-byte random key and format it as a valid IPFS swarm key.
  """
  # 32 bytes of cryptographically secure random data
  random_bytes = os.urandom(32)
  # Hex-encode them
  hex_str = binascii.hexlify(random_bytes).decode('utf-8')

  # Construct the file content
  swarm_key_data = (
    "/key/swarm/psk/1.0.0/\n"
    "/base16/\n"
    f"{hex_str}\n"
  )

  return swarm_key_data


if __name__ == "__main__":
  key_str = generate_swarm_key()
  print("Generated swarm.key content:")
  print(key_str)
  # Optionally save to a file
  with open("swarm.key", "w") as f:
    f.write(key_str)
  print("Swarm key written to swarm.key")
