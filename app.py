from flask import Flask, jsonify, request, render_template, redirect, url_for, make_response
from bank import BankAccounts, encrypt_challenge, is_valid
from bank import validation as val
        
    
# Initialize BankAccounts class
bank = BankAccounts()

# initialize app
app = Flask(__name__)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Step 2: verify challenge
        if 'decrypted_response' in request.form:
            username = request.form.get('username')
            response = request.form.get('decrypted_response')
            session_id = request.form.get('session_id')

            expected = bank.pending_challenges.get(username)
            if expected and response.strip() == expected.strip():
                # Success, remove challenge and continue
                del bank.pending_challenges[username]
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Decryption failed')


        # Step 1: username + password
        username = request.form.get('username')
        password = request.form.get('password')

        session_id = bank.login(username, password)

        if username == 'admin' and session_id:
            resp = make_response(redirect(url_for('dashboard')))
            resp.set_cookie(
                'session_id',
                session_id,
                httponly=True,
                secure=True,
                samesite='Lax'
            )
            return resp

        accounts = bank.load_accounts()
        account_id = bank.sessions[session_id]['account_id']

        if is_valid(bank.sessions, session_id):
            encrypted_challenge = encrypt_challenge(
                accounts=accounts, 
                account_id=account_id, 
                pending_challenges=bank.pending_challenges, 
                keypath=bank.get_admin_private_filepath(), 
                passphrase=bank.get_passphrase(), 
                word_list=bank.word_list
                )

            # Create a response and set cookie
            resp = make_response(render_template(
                'login.html',
                challenge=encrypted_challenge,
                username=username
            ))
            resp.set_cookie(
                'session_id',
                session_id,
                httponly=True,
                secure=True,
                samesite='Lax'
            )
            return resp
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')
    
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        public_key = request.form.get('public_key')

        if not val.is_valid_username(username):
            return render_template('register.html', 
                                   error='Username must be between 3 and 20 characters. Valid characters are a-z, A-z, 0-9, _')
        
        if not val.is_valid_password(password):
            return render_template('register.html', 
                                   error='Min 8 characters long, 1 uppercase and lowercase, digit and special character')

        if not username or not password or not confirm_password or not public_key:
            return render_template('register.html', error='All fields are required.')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')

        reply = bank.register(username, password, public_key)
        if reply['success']:
            return render_template('register.html', success='Account created successfully. You can now log in.')
        else:
            return render_template('register.html', error=reply['reason'])

    return render_template('register.html')



@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    session_id = request.cookies.get('session_id')

    if not is_valid(bank.sessions, session_id):
        return redirect(url_for('login'))
    
    balance = bank.get_balance(session_id)
    if balance is None:
        return render_template('login.html', error='Session expired or invalid')
    
    if request.method == 'POST':
        amount_str = request.form.get('amount')
        try:
            amount = val.parse_amount(amount_str)
            if amount is None:
                raise ValueError("Invalid amount format or value")
            new_balance = bank.add_balance(session_id, amount)
        except (TypeError, ValueError):
            new_balance = bank.get_balance(session_id)
    else:
        new_balance = bank.get_balance(session_id)

    username = bank.get_username(session_id)
    show_add = request.args.get('show_add') == '1'
    
    return render_template(
        'dashboard.html',
        balance=new_balance,
        username=username,
        show_add=show_add
        )

@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')


@app.route('/logout', methods=['POST'])
def logout():
    session_id = request.cookies.get('session_id')
    bank.logout(session_id)
    return redirect(url_for('login'))


@app.route('/pgp', methods=['GET'])
def pgp():
    with open('keys/admin_public.asc') as f:
        public_key = f.read()
    return render_template('pgp.html', public_key=public_key)


@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if request.method == 'POST':
        session_id = request.cookies.get('session_id')
        recipient = request.form.get('recipient', '').strip()
        amount_str = request.form.get('amount', '').strip()

        if amount is None:
            return render_template('transfer.html', error='Invalid amount format or value')

        if not is_valid(session_id):
            return redirect(url_for('login'))

        if not recipient or not amount_str:
            print(f"[DEBUG] Missing field(s): recipient={recipient}, amount={amount_str}")
            return render_template('transfer.html', error='All fields are required')
        
        try:
            amount = val.parse_amount(amount_str)
        except (TypeError, ValueError):
            return render_template('transfer.html', error='Invalid amount')
        
        result = bank.transfer(amount, session_id, recipient)
        if result['success']:
            return render_template('transfer.html', success=result['reason'])
        else:
            return render_template('transfer.html', error=result['reason'])
    
    # for GET requests
    session_id = request.cookies.get('session_id')
    return render_template('transfer.html')


@app.route('/admin')
def admin_panel():
    session_id = request.cookies.get('session_id')

    if not is_valid(bank.sessions, session_id):
        return redirect(url_for('login'))
    
    if not bank.is_admin(session_id):
        return 'Unauthorized', 403
    
    accounts = bank.load_accounts()

    users = [
        {
            'username': data['name'],
            'balance': data['balance'],
            'account_id': acc_id
        }
        for acc_id, data in accounts.items()
    ]

    return render_template('admin.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)