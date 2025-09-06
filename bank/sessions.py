import uuid, time

TIMEOUT_FIXED = 180 * 60    # 2h
TIMEOUT_ROLLING = 10 * 60   # 10 min

def create(sessions, account_id):
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        'account_id': account_id,
        'created_at': time.time(),
        'last_activity': time.time()
    }
    return session_id

def is_valid(sessions,session_id):
    session = sessions.get(session_id)
    if not session:
        return False
    
    now = time.time()

    # fixed timeout
    if now - session['created_at'] > TIMEOUT_FIXED:
        del sessions[session_id]
        return False
    
    # rolling timeout
    if now - session['last_activity'] > TIMEOUT_ROLLING:
        del sessions[session_id]
        return False
    
    # Extend session
    sessions[session_id]['last_activity'] = now
    return True


# Maybe later if needed
def cleanup_sessions(self):
    pass