import hashlib
import hmac
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, delete, func, text
from sqlalchemy.orm import Session
from .db import get_db
from .models import AuthSession, User, RateEvent

COOKIE = 'mistakedna_session'

def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def hash_password(password):
    salt = secrets.token_hex(16)
    key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return f'scrypt$16384$8$1${salt}${key.hex()}'

def check_password(password, encoded):
    try:
        _, n, r, p, salt, expected = encoded.split('$')
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

# A real hash makes unknown-account checks perform the same expensive operation.
DUMMY_HASH = hash_password('not-a-valid-account-password')

def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE)
    auth = db.get(AuthSession, digest(token)) if token else None
    if not auth or auth.expires_at <= now():
        raise HTTPException(401, 'Sign in to access your private learning records.')
    user = db.get(User, auth.user_id)
    if not user:
        raise HTTPException(401, 'Sign in again.')
    return user

def new_session(db, user_id, response, settings):
    token = secrets.token_urlsafe(32)
    db.execute(delete(AuthSession).where(AuthSession.expires_at < now()))
    db.add(AuthSession(token_hash=digest(token), user_id=user_id, expires_at=(datetime.now(timezone.utc)+timedelta(days=14)).isoformat(timespec='microseconds')))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=14*86400, httponly=True, secure=settings.secure_cookies, samesite='lax', path='/')


def rate_limit(db, bucket, limit, seconds):
    if db.bind.dialect.name == 'postgresql':
        lock_id = int.from_bytes(hashlib.sha256(bucket.encode()).digest()[:8], 'big', signed=True)
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key':lock_id})
    cutoff = (datetime.now(timezone.utc)-timedelta(seconds=seconds)).isoformat(timespec='microseconds')
    # Database-backed limits survive restart. Old metadata is bounded to 24 hours.
    old = (datetime.now(timezone.utc)-timedelta(days=1)).isoformat(timespec='microseconds')
    db.execute(delete(RateEvent).where(RateEvent.at < old))
    count = db.scalar(select(func.count()).select_from(RateEvent).where(RateEvent.bucket == bucket, RateEvent.at >= cutoff))
    if count >= limit:
        db.rollback()
        raise HTTPException(429, 'Too many requests. Please try again later.', headers={'Retry-After': str(seconds)})
    import uuid
    db.add(RateEvent(id=str(uuid.uuid4()), bucket=bucket, at=now()))
    db.commit()
