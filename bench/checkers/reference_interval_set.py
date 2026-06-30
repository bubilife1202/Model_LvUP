"""Reference implementation for T1 (IntervalSet). Used ONLY to generate and
validate hidden-test expectations — never shown to any model under test."""


class IntervalSet:
    def __init__(self):
        # disjoint, sorted, maximal: [lo, lo_closed, hi, hi_closed]
        self.ivs = []

    def add(self, lo, hi, lo_closed, hi_closed):
        if lo > hi:
            raise ValueError("lo > hi")
        if lo == hi and not (lo_closed and hi_closed):
            return  # empty interval: no-op
        new = [lo, bool(lo_closed), hi, bool(hi_closed)]
        keep = []
        for iv in self.ivs:  # ascending order; see soundness note in docs
            if self._mergeable(iv, new):
                new = self._merge(iv, new)
            else:
                keep.append(iv)
        keep.append(new)
        keep.sort(key=lambda iv: (iv[0], not iv[1]))
        self.ivs = keep

    @staticmethod
    def _mergeable(a, b):
        if a[0] > b[0]:
            a, b = b, a
        if b[0] < a[2]:
            return True
        if b[0] == a[2] and (a[3] or b[1]):
            return True
        return False

    @staticmethod
    def _merge(a, b):
        if a[0] < b[0]:
            lo, lc = a[0], a[1]
        elif b[0] < a[0]:
            lo, lc = b[0], b[1]
        else:
            lo, lc = a[0], a[1] or b[1]
        if a[2] > b[2]:
            hi, hc = a[2], a[3]
        elif b[2] > a[2]:
            hi, hc = b[2], b[3]
        else:
            hi, hc = a[2], a[3] or b[3]
        return [lo, lc, hi, hc]

    def remove(self, lo, hi, lo_closed, hi_closed):
        if lo > hi:
            raise ValueError("lo > hi")
        if lo == hi and not (lo_closed and hi_closed):
            return  # empty interval: no-op
        rlo, rlc, rhi, rhc = lo, bool(lo_closed), hi, bool(hi_closed)
        out = []
        for alo, alc, ahi, ahc in self.ivs:
            # overlap iff R starts before A ends and A starts before R ends,
            # counting shared endpoints only when both sides include them
            starts_before_a_ends = rlo < ahi or (rlo == ahi and rlc and ahc)
            ends_after_a_starts = alo < rhi or (alo == rhi and alc and rhc)
            if not (starts_before_a_ends and ends_after_a_starts):
                out.append([alo, alc, ahi, ahc])
                continue
            # left remainder: A ∩ (-inf, rlo] with rlo included iff R excludes it
            lhi, lhc = rlo, not rlc
            if lhi == ahi:
                lhc = lhc and ahc
            if alo < lhi or (alo == lhi and alc and lhc):
                out.append([alo, alc, lhi, lhc])
            # right remainder: A ∩ [rhi, +inf) with rhi included iff R excludes it
            nlo, nlc = rhi, not rhc
            if nlo == alo:
                nlc = nlc and alc
            if nlo < ahi or (nlo == ahi and nlc and ahc):
                out.append([nlo, nlc, ahi, ahc])
        out.sort(key=lambda iv: (iv[0], not iv[1]))
        self.ivs = out

    def contains(self, x):
        for lo, lc, hi, hc in self.ivs:
            if lo < x < hi:
                return True
            if x == lo and lc:
                return True
            if x == hi and hc:
                return True
        return False

    def canonical(self):
        if not self.ivs:
            return "{}"
        parts = []
        for lo, lc, hi, hc in self.ivs:
            if lo == hi:
                parts.append("{" + format(lo, "g") + "}")
            else:
                parts.append(
                    ("[" if lc else "(")
                    + format(lo, "g")
                    + ", "
                    + format(hi, "g")
                    + ("]" if hc else ")")
                )
        return " u ".join(parts)
