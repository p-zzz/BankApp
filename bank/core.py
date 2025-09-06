import os, uuid, time, hashlib
from bank.pgp_utils import save_encrypted_json, load_encrypted_json
from bank.sessions import create


class BankAccounts:

    def __init__(self):
        #self.users = {}     # user_hash → account_id
        #self.accounts = {}  # account_id → account data
        self.sessions = {}  # session_id → account_id
        self.pending_challenges = {}    # username → plaintext challenge
        self.word_list = [
            'anchor', 'banana', 'crystal', 'dynamo', 'ember', 'falcon', 'grove', 'harbor',
            'island', 'jungle', 'koala', 'lantern', 'meteor', 'nebula', 'oasis', 'plasma',
            'quartz', 'raven', 'saber', 'temple', 'utopia', 'vortex', 'wander', 'xenon',
            'yonder', 'zephyr'
        ]

        self.users_filepath = 'user/users.json'
        self.accounts_filepath = 'account/accounts.json'
        self.admin_private_filepath = 'keys/admin_private.asc'
        self.admin_public_filepath = 'keys/admin_public.asc'
        self.passphrase = os.environ.get("BANK_PASSPHRASE")


    def get_users_filepath(self):
        return self.users_filepath
    
    def get_accounts_filepath(self):
        return self.accounts_filepath
    
    def get_admin_private_filepath(self):
        return self.admin_private_filepath
    
    def get_admin_public_filepath(self):
        return self.admin_public_filepath
    
    def get_passphrase(self):
        return self.passphrase
    
    def get_username(self, session_id):
        if session_id not in self.sessions:
            return None
        accounts = self.load_accounts()
        account_id = self.sessions[session_id]['account_id']
        return accounts[account_id]['name']
    
    def hash_credentials(self, username, password):
        return hashlib.sha256((username + password).encode()).hexdigest()

    def load_users(self):
        print("[DEBUG] Calling load_users()")
        return load_encrypted_json(self.get_users_filepath(), self.passphrase, self.get_admin_private_filepath())
    
    def save_users(self, users_data):
        save_encrypted_json(
        self.get_users_filepath(),
        users_data,
        self.get_admin_public_filepath()
    )
        
    def load_accounts(self):
        print("[DEBUG] Calling load_accounts()")
        return load_encrypted_json(self.get_accounts_filepath(), self.passphrase, self.get_admin_private_filepath())
    
    def save_accounts(self, accounts_data):
        save_encrypted_json(
            self.get_accounts_filepath(),
            accounts_data,
            self.get_admin_public_filepath()
        )

    def register(self, username, password, public_key):
        print('[DEBUG] Calling load accounts')
        accounts = self.load_accounts()
        if any(acc['name'] == username for acc in accounts.values()):
            return {'success': False, 'reason': 'Username already exists'}
        user_hash = self.hash_credentials(username, password)
        account_id = str(uuid.uuid4())
        users = self.load_users()
        users[user_hash] = account_id
        accounts[account_id] = {
            'name': username,
            'balance': 0,
            'public_key': public_key,
        }
        print("[DEBUG] Users before save:", users)
        print("[DEBUG] Accounts before save:", accounts)
        self.save_users(users)
        self.save_accounts(accounts)
        
        print("[DEBUG] Register success")
        return {'success': True, 'reason': 'Account created successfully'}
    
    def login(self, username, password):
        user_hash = self.hash_credentials(username, password)

        # load and decrypt users file
        users = self.load_users()

        if user_hash not in users:
            return None     # Login failed
        session_id = create(self.sessions, users[user_hash])
        return session_id
    

    def logout(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]
            return {'success': True, 'reason': 'Logged out successfully'}
        else:
            return {'success': False, 'reason': 'Invalid session ID'}
        

    def get_balance(self, session_id):
        if session_id not in self.sessions:
            return None     # Invalid session
        accounts = self.load_accounts()
        account_id = self.sessions[session_id]['account_id']
        return accounts[account_id]['balance']
    
    
    def add_balance(self, session_id, amount):
        if session_id not in self.sessions:
            return None     # Invalid session
        accounts = self.load_accounts()
        account_id = self.sessions[session_id]['account_id']
        accounts[account_id]['balance'] += amount
        self.save_accounts(accounts)
        return accounts[account_id]['balance']
    

    def transfer(self, amount, session_id, recipient_username):
        if session_id not in self.sessions:
            print('[ERROR] Invalid session')
            return {'success': False, 'reason': 'Invalid session'}
        if amount <= 0:
            print('[ERROR] Amount must be positive')
            return {'success': False, 'reason': 'Amount must be positive'}
        
        accounts = self.load_accounts()

        sender_id = self.sessions[session_id]['account_id']

        # Find recipient ID
        recipient_id = None
        for acc_id, acc_data in accounts.items():
            if acc_data['name'] == recipient_username:
                recipient_id = acc_id
                break

        if recipient_id is None:
            print('[ERROR] Recipient not found')
            return {'success': False, 'reason': 'Recipient not found'}
        if sender_id == recipient_id:
            print('[ERROR] Cannot transfer to self')
            return {'success': False, 'reason': 'Cannot transfer to self'}
        if accounts[sender_id]['balance'] < amount:
            print('[ERROR] Insufficient funds')
            return {'success': False, 'reason': 'Insufficient funds'}
        # Perform transfer
        accounts[sender_id]['balance'] -= amount
        accounts[recipient_id]['balance'] += amount

        self.save_accounts(accounts)

        print('[DEBUG] Transfer successful')
        return {'success': True, 'reason': 'Transfer successful'}
    

    def is_admin(self, session_id):
        username = self.get_username(session_id)
        return username == 'admin'