import os, pgpy, json, random

def load_admin_privkey(keypath):
    try:
        key, _ = pgpy.PGPKey.from_file(keypath)
        return key
    except Exception as e:
        print(f'[ERROR] Failed to load admin private key: {e}')
        return None
    
def load_admin_pubkey(keypath):
    try:
        key, _ = pgpy.PGPKey.from_file(keypath)
        if not key.is_public:
            print('[ERROR] Loaded key is not public')
            return None
        return key
    except Exception as e:
        print(f'[ERROR] Failed to load admin public key: {e}')
        return None

def save_encrypted_json(filepath, new_data, keypath):
    try:
        # Only try to load existing data if file exists
        if os.path.exists(filepath):
            current_data = load_encrypted_json(filepath)
        else:
            current_data = {}

        print(f"[DEBUG] Saving encrypted file {filepath} with data: {current_data}")
        current_data.update(new_data)

        # Encrypt with public key
        pubkey = load_admin_pubkey(keypath)
        message = pgpy.PGPMessage.new(json.dumps(current_data, indent=2))
        print('DEBUG: pubkey loaded ?', pubkey)
        if pubkey is None:
            raise Exception("Public key not loaded. Check admin_public.asc path and format.")
        encrypted = pubkey.encrypt(message)

        with open(filepath, 'w') as f:
            f.write(str(encrypted))

    except Exception as e:
        print(f'[ERROR] Failed to encrypt/save {filepath}: {e}')


def load_encrypted_json(filepath, passphrase, keypath):
    try:
        with open(filepath, 'r') as f:
            encrypted_blob = f.read()

        privkey = load_admin_privkey(keypath)
        with privkey.unlock(passphrase):
            message = pgpy.PGPMessage.from_blob(encrypted_blob)
            decrypted = privkey.decrypt(message)

        return json.loads(str(decrypted.message))
        
    except (FileNotFoundError, json.JSONDecodeError, pgpy.errors.PGPError) as e:
        print(f"[WARN] Failed to decrypt {filepath}: {type(e).__name__}: {e}")
        return {}
    

def generate_challenge(word_list, num_words=4):
        return ' '.join(random.choice(word_list) for _ in range(num_words))
    

def encrypt_challenge(accounts, account_id, pending_challenges, keypath, passphrase, word_list):
    keyblob = accounts[account_id]['public_key']
    username = accounts[account_id]['name']
    pubkey, _ = pgpy.PGPKey.from_blob(keyblob)

    challenge = generate_challenge(word_list)
    pending_challenges[username] = challenge   # store plaintext for verification

    # Create message
    message = pgpy.PGPMessage.new(challenge)

    privkey = load_admin_privkey(keypath)
    with privkey.unlock(passphrase):
        message |= privkey.sign(message)
        encrypted = pubkey.encrypt(message)

    return str(encrypted)