#!/usr/bin/env python3
"""Cube-and-conquer worker: python3 cube.py puzzle.cnf idx deadline_epoch outfile
Adds unit clauses for cube idx over the 4 most-occurring vars, runs several kissat configs in parallel."""
import sys, os, time, subprocess, collections, shutil

def parse(path):
    nv = 0; cl = []
    cur = []
    for line in open(path):
        if not line or line[0] in 'cp%': 
            if line.startswith('p cnf'): nv = int(line.split()[2])
            continue
        for t in line.split():
            x = int(t)
            if x == 0:
                if cur: cl.append(cur)
                cur = []
            else: cur.append(x)
    return nv, cl

def main():
    path, idx, deadline, out = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    nv, cl = parse(path)
    cnt = collections.Counter(abs(l) for c in cl for l in c)
    top = [v for v, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:4]]
    units = [(top[b] if (idx >> b) & 1 else -top[b]) for b in range(4)]
    print('nproc', os.cpu_count(), 'vars', nv, 'clauses', len(cl), 'cube vars', top, 'units', units, flush=True)
    with open('cube.cnf', 'w') as f:
        f.write('p cnf %d %d\n' % (nv, len(cl) + 4))
        for c in cl: f.write(' '.join(map(str, c)) + ' 0\n')
        for u in units: f.write('%d 0\n' % u)
    budget = max(5, int(deadline - time.time() - 60))
    print('budget seconds', budget, flush=True)
    kissat = shutil.which('kissat') or './kissat/build/kissat'
    cfgs = [['--seed=1'], ['--seed=2', '--walkinitially=true'], ['--seed=3', '--stable=2'], ['--seed=4', '--target=2']]
    procs = []
    for i, extra in enumerate(cfgs[:max(1, min(4, os.cpu_count() or 1))]):
        cmd = ['timeout', str(budget), kissat, '-q', '--sat'] + extra + ['cube.cnf']
        o = open('out%d.txt' % i, 'w')
        procs.append((subprocess.Popen(cmd, stdout=o, stderr=subprocess.STDOUT), 'out%d.txt' % i))
    t0 = time.time(); found = None
    while procs and not found:
        time.sleep(0.5)
        for p, fn in list(procs):
            if p.poll() is not None:
                procs.remove((p, fn))
                if p.returncode == 10: found = fn; break
    for p, fn in procs:
        try: p.kill()
        except Exception: pass
    print('elapsed', round(time.time() - t0, 1), 'found', found, flush=True)
    if not found:
        return 0
    val = {}
    for line in open(found):
        if line.startswith('v '):
            for t in line.split()[1:]:
                x = int(t)
                if x: val[abs(x)] = 1 if x > 0 else 0
    bits = ''.join(str(val.get(v, 0)) for v in range(1, nv + 1))
    ok = all(any((val.get(abs(l), 0) == 1) == (l > 0) for l in c) for c in cl)
    print('verified', ok, flush=True)
    if ok:
        open(out, 'w').write(bits)
    return 0

sys.exit(main())
