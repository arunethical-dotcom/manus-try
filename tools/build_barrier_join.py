"""joins barrier pieces along the wall line (never across a gate)"""
import numpy as np, cv2
def join(B, L, WW, WH):
    """join the strip pieces along the wall line: nearest-neighbour links (shortest first, union-find), never across a
    gate, so the barrier becomes one band broken only at the two gates"""
    small = cv2.resize(B.astype(np.uint8), (WW // 8, WH // 8), interpolation=cv2.INTER_NEAREST)
    n, lab, st, _ = cv2.connectedComponentsWithStats(small, connectivity=8)
    comps = [i for i in range(1, n) if st[i, 4] >= 4]
    pts = {i: np.argwhere(lab == i)[:, ::-1] for i in comps}
    gates = [(g[0] // 8, g[1] // 8) for g in L["gates"].values()]
    pairs = []
    for ii, i in enumerate(comps):
        for j in comps[ii + 1:]:
            a_, b_ = pts[i], pts[j]
            if len(a_) > 400: a_ = a_[::len(a_) // 400]
            if len(b_) > 400: b_ = b_[::len(b_) // 400]
            d = np.sqrt(((a_[:, None, :] - b_[None, :, :]) ** 2).sum(-1))
            k = np.unravel_index(np.argmin(d), d.shape)
            if d[k] > 160:
                continue
            pa, pb = a_[k[0]], b_[k[1]]
            mid = (pa + pb) / 2
            if any(abs(mid[0] - gx) < 25 and abs(mid[1] - gy) < 70 for gx, gy in gates):
                continue
            pairs.append((float(d[k]), i, j, tuple(int(v) for v in pa), tuple(int(v) for v in pb)))
    pairs.sort()
    par = {i: i for i in comps}
    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    out = B.copy()
    for d, i, j, pa, pb in pairs:
        if f(i) == f(j):
            continue
        par[f(i)] = f(j)
        m = np.zeros((WH, WW), np.uint8)
        cv2.line(m, (pa[0] * 8 + 4, pa[1] * 8 + 4), (pb[0] * 8 + 4, pb[1] * 8 + 4), 1, 28)
        out |= m.astype(bool)
    return out


