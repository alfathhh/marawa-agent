from __future__ import annotations
import asyncio
import secrets
import time
from datetime import UTC, datetime
from .models import SessionState, Message

IDLE_SECONDS = 7200
MAX_SESSIONS = 100
MAX_MESSAGES = 40


def now():
    return datetime.now(UTC)


def token(prefix):
    return prefix + secrets.token_urlsafe(18)


class SessionStore:
    def __init__(self, generation=None, clock=time.time):
        self.generation = generation or token("boot_")
        self.clock = clock
        self.sessions = {}
        self._locks = {}

    def _expired(self, s):
        return self.clock() - s.last_active_at.timestamp() > IDLE_SECONDS

    def create(self):
        self.purge()
        if len(self.sessions) >= MAX_SESSIONS:
            raise RuntimeError("session_capacity")
        t = now()
        sid = token("pv1_")
        s = SessionState(sid, self.generation, t, t, lock=asyncio.Lock())
        self.sessions[sid] = s
        self._locks[sid] = s.lock
        return s

    def purge(self):
        for sid, s in list(self.sessions.items()):
            if self._expired(s):
                self.delete(sid)

    def get(self, sid, generation=None):
        s = self.sessions.get(sid)
        if not s:
            return None
        if generation and generation != self.generation:
            raise ValueError("generation_mismatch")
        if self._expired(s):
            self.delete(sid)
            raise TimeoutError("session_expired")
        s.last_active_at = now()
        return s

    def delete(self, sid):
        self.sessions.pop(sid, None)
        self._locks.pop(sid, None)

    def append_message(self, s, message):
        s.messages.append(message)
        del s.messages[:-MAX_MESSAGES]

    def commit(self, s, message_id, response):
        if message_id in s.response_cache:
            return s.response_cache[message_id]
        s.state_version += 1
        s.response_cache[message_id] = response
        while len(s.response_cache) > 50:
            del s.response_cache[next(iter(s.response_cache))]
        return response

    def cached(self, s, message_id):
        return s.response_cache.get(message_id)

    def version_ok(self, s, version):
        return version == s.state_version

    def new_message(self, role, content, message_id):
        return Message(role, content, message_id, now())


store = SessionStore()


def request_topic_switch(session, query, *, is_follow_up=False):
    if is_follow_up or session.frame is None:
        return False
    session.pending_topic = query
    return True


def confirm_topic_switch(session):
    query = session.pending_topic
    session.pending_topic = None
    if query is not None:
        session.frame = None
    return query


def cancel_topic_switch(session):
    session.pending_topic = None
