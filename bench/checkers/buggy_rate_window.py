"""The buggy module exactly as given to models in T2 — for checker validation."""
import collections


class RateWindow:
    def __init__(self, limit, window_s):
        self.limit = limit
        self.window_s = window_s
        self.calls = {}
        self.bans = {}

    def ban(self, identity, until):
        self.bans[identity] = until

    def _banned(self, identity, now):
        until = self.bans.get(identity)
        return until is not None and now <= until

    def allow(self, identity, now):
        q = self.calls.setdefault(identity, collections.deque())
        while q and q[0] < now - self.window_s:
            q.popleft()
        if self._banned(identity, now):
            q.append(now)
            return False
        if len(q) > self.limit:
            return False
        q.append(now)
        return True
