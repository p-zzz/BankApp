def list_users(accounts):
    return [(aid, data['name'], data['balance']) for aid, data in accounts.items()]

def remove_user(accounts, account_id):
    if account_id in accounts:
        del accounts[account_id]
        return True
    return False

def update_balance(accounts, account_id, new_balance):
    if account_id in accounts:
        accounts[account_id]['balance'] = new_balance
        return True
    return False


def kill_switch():
    return True
