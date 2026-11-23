import html, sys
E = html.escape
out = []
W = out.append

# ---------- helpers ----------
def stacked(rows, legend=None, unit=''):
    """rows: (label, [(role, name, count)], note)"""
    h = ['<div class="chart">']
    for label, parts, note in rows:
        tot = sum(p[2] for p in parts)
        h.append(f'<div class="row{"" if label else " nolabel"}"><div class="rl">{label}</div><div class="bar">')
        for role, name, c in parts:
            if c <= 0: continue
            pct = 100 * c / tot
            full = f'{name} {c:g}'.strip()
            txt = E(full) if pct >= 2.2 * len(full) + 4 else (f'{c:g}' if pct >= 6 else '')
            h.append(f'<span class="seg {role}" style="flex:{c} 1 0" data-tip="{E(name)}: {c:g} of {tot:g} ({pct:.0f}%)">{txt}</span>')
        h.append(f'</div><div class="rn">{note}</div></div>')
    if legend:
        h.append('<div class="legend">' + ''.join(f'<span><i class="sw {r}"></i>{E(n)}</span>' for r, n in legend) + '</div>')
    h.append('</div>')
    return ''.join(h)

def hbars(rows, mx, cls='d', suffix=''):
    """rows: (label, value, valuetext)"""
    h = ['<div class="chart">']
    for label, v, vt in rows:
        h.append(f'<div class="row"><div class="rl">{label}</div><div class="track"><span class="fill {cls}" style="width:{100*v/mx:.1f}%" data-tip="{E(str(label))}: {E(vt)}"></span><b>{E(vt)}</b></div></div>')
    h.append('</div>')
    return ''.join(h)

def prompt(lines, who='Prompt'):
    return f'<div class="prompt"><div class="eyebrow">{who}</div>' + ''.join(f'<p>{l}</p>' for l in lines) + '</div>'

TASK = '<span class="task">+ the task</span>'
def code(src, cap=None):
    c = f'<figcaption>{cap}</figcaption>' if cap else ''
    return f'<figure class="code">{c}<pre><code>{src}</code></pre></figure>'

def shot(path, alt, cap):
    return f'<figure class="shot"><img src="{path}" alt="{E(alt)}" loading="lazy"><figcaption>{cap}</figcaption></figure>'

CH = {'ok': ('ok', '✓', 'holds'), 'part': ('part', '◐', 'partly holds'), 'no': ('no', '✕', 'does not hold'), 'new': ('new', '＋', 'was not in my notes')}
def finding(fid, src, claim, verdict, vtext, left, right, catches, wide=None):
    cls, icon, lab = CH[verdict]
    W(f'<article class="f" id="{fid}"><header><div class="meta"><span class="src">{src}</span>'
      f'<span class="chip {cls}"><i>{icon}</i>{vtext or lab}</span></div><h3>{claim}</h3></header>')
    W(f'<div class="two"><div class="col">{left}</div><div class="col">{right}</div></div>')
    if wide: W(wide)
    if catches:
        W('<ul class="catch">' + ''.join(f'<li>{c}</li>' for c in catches) + '</ul>')
    W('</article>')

def theme(tid, title, lead):
    W(f'<section class="theme" id="{tid}"><h2>{title}</h2><p class="lead">{lead}</p>')
def endtheme(): W('</section>')

# ---------- page ----------
W('''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>One Algorithm Per Task</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
<style>
/* layout: one reading column; each finding = claim on top, "what was asked" left, "what came out" right */
:root{
  --bg:#f7f8fa; --panel:#ffffff; --ink:#14181f; --ink2:#4a5261; --ink3:#7a8292; --line:#dfe3ea; --mark:#fff1b8;
  --d:#2a78d6; --a1:#eb6834; --a2:#1baf7a; --a3:#eda100; --a4:#e87ba4; --x:#c9cdd6; --xink:#3b4250;
  --good:#0ca30c; --warn:#b97a00; --bad:#d03b3b; --newc:#6250d6;
  --sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif; --mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#12151a; --panel:#1b1f27; --ink:#eceef2; --ink2:#b4bac6; --ink3:#868d9b; --line:#2e3440; --mark:#5a4a12;
  --d:#3987e5; --a1:#d95926; --a2:#199e70; --a3:#c98500; --a4:#d55181; --x:#4a505d; --xink:#e3e6ec;
  --good:#3fbf3f; --warn:#e0a630; --bad:#ef6b6b; --newc:#9085e9; color-scheme:dark } }
:root[data-theme="dark"]{
  --bg:#12151a; --panel:#1b1f27; --ink:#eceef2; --ink2:#b4bac6; --ink3:#868d9b; --line:#2e3440; --mark:#5a4a12;
  --d:#3987e5; --a1:#d95926; --a2:#199e70; --a3:#c98500; --a4:#d55181; --x:#4a505d; --xink:#e3e6ec;
  --good:#3fbf3f; --warn:#e0a630; --bad:#ef6b6b; --newc:#9085e9; color-scheme:dark }
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 var(--sans)}
.wrap{max-width:1060px;margin:0 auto;padding-block:28px 80px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
h1{font-size:clamp(1.9rem,4.5vw,2.9rem);line-height:1.08;margin:0 0 .5rem;letter-spacing:-.02em;text-wrap:balance}
h2{font-size:1.5rem;margin:0 0 .2rem;letter-spacing:-.01em;text-wrap:balance}
h3{font-size:1.22rem;line-height:1.3;margin:.35rem 0 0;font-weight:600;text-wrap:balance}
p{margin:0}
.sub{color:var(--ink2);font-size:1.1rem;max-width:62ch}
.lead{color:var(--ink2);max-width:66ch;margin-bottom:1rem}
nav{display:flex;flex-wrap:wrap;gap:8px;margin:1.4rem 0 0}
nav a{font:500 .85rem var(--sans);color:var(--ink);text-decoration:none;border:1px solid var(--line);background:var(--panel);padding:.35rem .7rem;border-radius:999px}
nav a:hover,nav a:focus-visible{border-color:var(--d);outline:none}
.theme{margin-top:3.2rem}
.f{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-top:14px}
.meta{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.src{font:500 .74rem var(--mono);color:var(--ink3);letter-spacing:.03em;text-transform:uppercase}
.chip{display:inline-flex;align-items:center;gap:.35rem;font:600 .74rem var(--sans);padding:.12rem .55rem;border-radius:999px;border:1px solid currentColor}
.chip i{font-style:normal}
.chip.ok{color:var(--good)} .chip.part{color:var(--warn)} .chip.no{color:var(--bad)} .chip.new{color:var(--newc)}
.two{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,6fr);gap:18px;margin-top:14px;align-items:start}
.two.even{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
.col{min-width:0;display:flex;flex-direction:column;gap:12px}
@media (max-width:760px){.two,.two.even{grid-template-columns:minmax(0,1fr)}}
.prompt{border:1px solid var(--line);border-left:3px solid var(--ink3);border-radius:6px;padding:10px 12px;font:400 .86rem/1.5 var(--mono);background:var(--bg);overflow-wrap:anywhere}
.prompt p+p{margin-top:.45rem}
.eyebrow{font:600 .68rem var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--ink3);margin-bottom:.3rem}
mark{background:var(--mark);color:inherit;padding:0 .15em;border-radius:3px}
.task{color:var(--ink3);font-style:italic}
.did{font-size:.95rem;color:var(--ink2)}
.did b{color:var(--ink)}
.chart{display:flex;flex-direction:column;gap:7px}
.ct{font:600 .8rem var(--sans);color:var(--ink2);margin-bottom:-2px}
.row{display:grid;grid-template-columns:minmax(84px,150px) minmax(0,1fr);gap:4px 10px;align-items:center}
.rl{font-size:.83rem;color:var(--ink2);line-height:1.25;overflow-wrap:anywhere}
.rn{grid-column:2;font-size:.74rem;color:var(--ink3);margin-top:-3px}
.rn:empty{display:none}
.row.nolabel{grid-template-columns:minmax(0,1fr)}.row.nolabel .rl{display:none}.row.nolabel .rn{grid-column:1}
.bar{display:flex;gap:2px;height:24px}
.seg{min-width:3px;display:flex;align-items:center;justify-content:center;font:600 .72rem var(--sans);white-space:nowrap;overflow:hidden;color:#fff}
.seg:first-child{border-radius:4px 0 0 4px}.seg:last-child{border-radius:0 4px 4px 0}.seg:only-child{border-radius:4px}
.d{background:var(--d)} .a1{background:var(--a1)} .a2{background:var(--a2);color:#0b0b0b} .a3{background:var(--a3);color:#0b0b0b} .a4{background:var(--a4);color:#0b0b0b} .x{background:var(--x);color:var(--xink)}
.track{display:flex;align-items:center;gap:8px;height:20px}
.fill{height:16px;border-radius:0 4px 4px 0;min-width:2px}
.track b{font:600 .8rem var(--sans);font-variant-numeric:tabular-nums}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.76rem;color:var(--ink2);margin-top:2px}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.catch{margin:14px 0 0;padding:10px 0 0 1.1rem;border-top:1px solid var(--line);font-size:.9rem;color:var(--ink2)}
.catch li+li{margin-top:.25rem}
.catch b{color:var(--ink)}
figure{margin:0}
.code{border:1px solid var(--line);border-radius:6px;overflow:hidden;background:var(--bg)}
.code figcaption,.shot figcaption{font-size:.76rem;color:var(--ink3);padding:6px 10px}
.code figcaption{border-bottom:1px solid var(--line)}
pre{margin:0;padding:10px 12px;overflow-x:auto;font:400 .78rem/1.5 var(--mono)}
pre .hl{background:var(--mark);border-radius:3px}
pre .dim{color:var(--ink3)}
.shot{border:1px solid var(--line);border-radius:6px;overflow:hidden;margin-top:14px}
.shot{background:#fff}.shot figcaption{background:var(--panel)}
.shot img{display:block;width:auto;max-width:100%;height:auto;margin:0 auto}
.big{display:flex;flex-wrap:wrap;gap:10px 26px}
.big div{min-width:0}
.big b{display:block;font:700 1.7rem/1.1 var(--sans);font-variant-numeric:tabular-nums}
.big span{font-size:.8rem;color:var(--ink2)}
.fork{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px}
@media (max-width:520px){.fork{grid-template-columns:minmax(0,1fr)}}
.branch{border:1px solid var(--line);border-radius:6px;padding:8px 10px;background:var(--bg)}
.branch .tok{font:600 .86rem var(--mono);background:var(--mark);padding:0 .3em;border-radius:3px}
.branch p{font-size:.8rem;color:var(--ink2);margin-top:.3rem}
details{margin-top:8px;font-size:.85rem}
summary{cursor:pointer;color:var(--ink2)}
summary:focus-visible,a:focus-visible{outline:2px solid var(--d);outline-offset:2px}
table{border-collapse:collapse;width:100%;font-size:.86rem}
th,td{text-align:left;padding:5px 10px 5px 0;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--ink2)}
.scroll{overflow-x:auto}
#tip{position:fixed;z-index:20;pointer-events:none;background:var(--ink);color:var(--bg);font:500 .76rem var(--sans);padding:4px 8px;border-radius:4px;max-width:260px}
footer{margin-top:3rem;color:var(--ink3);font-size:.84rem;max-width:70ch}
footer a{color:inherit}
</style></head><body><div class="wrap">''')

W('''<header>
<h1>Ask a code model for a program and it writes the same algorithm every time.</h1>
<p class="sub">An AI scientist spent 10 rounds and 56 experiments trying to make it write a different one. This page shows what was asked and what came out. Every number was checked against the run's stored result files.</p>
<nav aria-label="Sections">
<a href="#setup">The setup</a><a href="#same">Sampling doesn't help</a><a href="#words">Words that work</a><a href="#bans">Bans that don't</a><a href="#token">One token decides</a><a href="#inside">Poking inside</a><a href="#origin">Where it comes from</a><a href="#invent">Can it invent?</a><a href="#tasks">Tasks</a>
</nav></header>''')

# ---------- setup ----------
theme('setup', 'The setup', 'Mostly Qwen3-8B with thinking off. One user message, no system prompt. The model returns a Python function, and the run labels which algorithm it is by executing it.')
W('<article class="f"><header><div class="meta"><span class="src">task T1 · grid path</span></div><h3>The task accepts any valid path. The model writes BFS.</h3></header><div class="two">')
W('<div class="col">' + prompt(['Please solve the following programming task.',
   'Task: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. […] <mark>Any valid path is accepted; it does not have to be the shortest.</mark> […]',
   'Use only the Python standard library. Return only one ```python code block […]']) +
  '<details><summary>Full task text</summary><div class="prompt" style="margin-top:8px"><p>Task: write a Python function solve(grid, start, goal) that finds a path between two cells of a grid. grid is a list of equal-length strings with between 1 and 30 rows and between 1 and 30 columns; the character . is a free cell and the character # is a wall. start and goal are (row, col) tuples of 0-based indices. A move goes to one of the 4 orthogonal neighbours (up, down, left, right) and may not leave the grid or enter a wall. Return a list of (row, col) tuples that begins with start, ends with goal, and in which consecutive cells are neighbours and every cell is free. Any valid path is accepted; it does not have to be the shortest. If start equals goal and the cell is free, return [start]. If no path exists, or start or goal is a wall, return [].</p><p>Use only the Python standard library. Return only one ```python code block containing the function solve and any helpers, with no example usage and no explanation.</p></div></details></div>')
W('<div class="col">' + stacked([
    ('T1 grid path', [('d', 'BFS', 797), ('x', 'other', 3)], '800 samples across every temperature setting'),
    ('T2 weighted shortest path', [('d', 'Dijkstra', 797), ('x', 'other', 3)], '800 samples'),
    ('13 more textbook tasks', [('d', 'one algorithm', 649), ('x', 'other', 1)], '50 samples each: 50/50 on twelve, 49/50 on one'),
  ]) + code(E('''    # BFS setup
    queue = deque()
    queue.append((start[0], start[1], [start]))
    visited = set()
    visited.add((start[0], start[1]))

    while queue:
        r, c, path = queue.popleft()'''), 'What it writes, every time (Qwen3-8B, real sample)') + '</div></div></article>')
endtheme()

# ---------- sampling ----------
theme('same', 'Sampling settings don\'t change the idea', 'More randomness gives you more ways of writing the same algorithm.')
finding('n4', 'my note 4 · R1E6', 'Temperature and random seeds only rephrase.', 'ok', 'holds on these tasks',
  prompt(['Here is a programming task. <mark>seed=d32qxk4nt43</mark>', TASK], 'Prompt · random seed') +
  prompt(['Here is a programming task. <mark>seed=(horse chair roof love)</mark>', TASK], 'Prompt · word seed') +
  '<p class="did">Temperature swept over <b>0.3, 0.7, 1.0, 1.3</b>, with top-k 10 and top-p 0.95, thinking off and on.</p>',
  '<div class="ct">Grid path task: algorithm written, 100 samples per row</div>' + stacked([
    ('T = 0.3', [('d', 'BFS', 100)], ''), ('T = 0.7', [('d', 'BFS', 99), ('a1', 'DFS', 1)], ''),
    ('T = 1.0', [('d', 'BFS', 100)], ''), ('T = 1.3', [('d', 'BFS', 99), ('a1', 'DFS', 1)], 'top-k 10 sampling'),
    ('random seed string', [('d', 'BFS', 100)], 'shift vs baseline: +1 point'),
  ]) + '<div class="big"><div><b>3–4 → 24–36</b><span>distinct phrasings, T 0.3 → 1.3</span></div><div><b>1 → 1–2</b><span>distinct algorithms</span></div></div>',
  ['Same seed, 20 seeds: temperature changed the algorithm in <b>0 of 20</b>, also with thinking on (R4E21).',
   'Only true where the model has one answer. On tasks where it already writes two algorithms, temperature shifts the mix. It never adds a third.'])
endtheme()

# ---------- words that work ----------
theme('words', 'Words that do move it', 'Naming an algorithm in the prompt is the strongest lever in the whole run, even when you name it in order to forbid it.')
finding('n1', 'my note 1 · R1E1', 'Just mention an algorithm and the model writes it. Not always 100%.', 'part', '100% for 2 of 9',
  prompt(['<mark>Depth-first search (DFS) is one well-known approach to this task</mark>; implement any correct algorithm.', TASK]) +
  '<p class="did">The prompt explicitly says <b>any</b> algorithm is fine. Without the mention, every one of these is at 0%.</p>',
  '<div class="ct">Programs that implement the mentioned algorithm (of 50)</div>' + hbars([
    ('DFS', 100, '100%'), ('Bellman-Ford / SPFA', 100, '100%'), ('Floyd-Warshall', 86, '86%'), ('IDDFS', 72, '72%'), ('A*', 56, '56%'),
    ('bidirectional BFS', 10, '10%'), ('Dijkstra on a grid', 0, '0%'), ('Dial', 0, '0%'), ('bidirectional Dijkstra', 0, '0%')], 100),
  ['Counts all programs, working or not: mention-DFS gives 50/50 DFS but only <b>15 of 50 pass</b> the tests.'])

finding('n5', 'my note 5 · R2E9', 'Ban the default and you get exactly one substitute.', 'ok', 'holds on the two path tasks',
  prompt(['<mark>Do not use breadth-first search (BFS) for this task.</mark>', TASK]) +
  prompt(['<mark>Do not use Dijkstra\'s algorithm for this task.</mark>', TASK]),
  stacked([
    ('grid path, no ban', [('d', 'BFS', 100)], ''),
    ('grid path, BFS banned', [('a1', 'DFS', 86), ('d', 'BFS', 14)], ''),
    ('shortest path, no ban', [('d', 'Dijkstra', 100)], ''),
    ('shortest path, Dijkstra banned', [('a1', 'Bellman-Ford', 83), ('d', 'Dijkstra', 16), ('x', 'other', 1)], ''),
  ], [('d', 'the default'), ('a1', 'the substitute'), ('x', 'other')]),
  ['Fragile. With 10 other wordings of the same ban, <b>62 of 100</b> are still BFS (R1E2). Only <b>5 of 12</b> other tasks obey a single ban at all (R3E13).',
   'Show a solution in the prompt, then ban it: the model goes back to its own default in 24 of 31 cases (R3E14).'])

finding('seed', 'aside in my notes · R1E6', 'A story that implies the approach works too.', 'part', 'works here, unstable later',
  prompt(['Here is a programming task. <mark>News spreads through a kingdom in rounds. In each round, every road carries a message from its source town to its destination town announcing how long the trip took so far plus the road\'s own travel time. Each town keeps only the shortest total it has ever heard. Once a whole round passes in which no town hears anything better, every town knows its true travel time.</mark>', TASK]),
  stacked([
    ('shortest path, plain', [('d', 'Dijkstra', 99), ('x', 'other', 1)], ''),
    ('with the story', [('a1', 'Bellman-Ford', 61), ('d', 'Dijkstra', 38), ('x', 'other', 1)], ''),
  ], [('d', 'the default'), ('a1', 'what the story describes')]),
  ['Later rounds got 15 of 50, and once 0 of 30, with similar stories.'])
endtheme()

# ---------- bans that don't ----------
theme('bans', 'Bans that don\'t work', 'Forbid the whole repertoire and the model keeps the algorithm and drops the name.')
finding('n5b', 'my note 5 · R2E9', 'Ban five algorithms and the model writes a banned one anyway.', 'ok', 'holds on the grid task',
  prompt(['<mark>Do not use breadth-first search (BFS), depth-first search (DFS), iterative deepening DFS (IDDFS), A* search or greedy best-first search for this task.</mark>', TASK]) +
  code('<span class="dim"># Use a set to keep track of visited cells</span>\nvisited = set()\n<span class="hl"># Use a queue for BFS-like traversal\n# without using BFS</span>\nqueue = [(start, [start])]\nvisited.add(start)\n\nwhile queue:\n    current, path = queue.pop(0)', 'Qwen3-8B under the five-name ban (real sample; comment wrapped here)'),
  '<div class="ct">Grid path, 100 samples per ban list</div>' + stacked([
    ('no ban', [('d', 'BFS', 100)], ''),
    ('1 name: BFS', [('a2', 'DFS (allowed)', 86), ('d', 'BFS', 14)], ''),
    ('4 names, DFS left free', [('a2', 'DFS (allowed)', 37), ('d', 'BFS', 63)], ''),
    ('4 names incl. DFS', [('d', 'BFS', 59), ('a1', 'DFS', 26), ('a1', 'greedy', 2), ('x', 'other', 13)], ''),
    ('5 names', [('d', 'BFS', 63), ('a1', 'DFS', 36), ('a1', 'IDDFS', 1)], '0 of 100 comply'),
  ], [('d', 'banned default, written anyway'), ('a1', 'another banned one'), ('a2', 'an allowed algorithm'), ('x', 'other')]),
  ['Path-task result. On other tasks two-name bans are obeyed (k-th smallest 1.00, find duplicate 0.96).',
   'Listing alternatives can backfire: on k-th smallest, a prompt banning five named algorithms gives <b>50 of 50 quickselect</b>, one of the banned ones (R3E18).'])

finding('n11', 'my note 11 · R9E45', 'Most models rename; they don\'t obey.', 'part', 'true for most models',
  '<p class="did">Same five-name ban, <b>10 model configurations</b>, 546 programs. Each program is checked twice: does the text avoid the banned names, and does the running code avoid the banned search order?</p>' +
  code(E('''    from collections import deque
    q = deque()
    q.append((start, [start]))
    visited.add(start)
    while q:
        current, path = q.popleft()'''), 'Qwen3-14B with thinking. No banned word anywhere. It is BFS.') +
  '<div class="prompt"><div class="eyebrow">Last line of its reasoning</div><p>"Since I\'m out of ideas, I\'ll proceed with the BFS code, assuming that the problem\'s restriction is a mistake, or that I\'m missing something."</p></div>',
  '<div class="ct">All 10 configurations pooled</div>' + stacked([
    ('546 programs', [('a1', 'renamed', 371), ('a2', 'really complies', 68), ('x', 'uses a banned name', 107)], ''),
  ]) + '<div class="ct" style="margin-top:8px">By model (runtime instrument)</div>' + stacked([
    ('Qwen3-8B think', [('a1', 'renamed', 20), ('a2', 'complies', 0), ('x', 'banned name', 10)], ''),
    ('Llama-3.1-8B', [('a1', 'renamed', 21), ('a2', 'complies', 27), ('x', 'banned name', 2)], ''),
    ('Qwen3-14B', [('a1', 'renamed', 47), ('a2', 'complies', 0), ('x', 'banned name', 3)], ''),
    ('Qwen3-14B think', [('a1', 'renamed', 35), ('a2', 'complies', 6), ('x', 'banned name', 5)], ''),
    ('Qwen3-32B', [('a1', 'renamed', 28), ('a2', 'complies', 7), ('x', 'banned name', 14)], ''),
    ('Qwen3-32B think', [('a1', 'renamed', 47), ('a2', 'complies', 16), ('x', 'banned name', 8)], 'by the second instrument: 25 renamed, 35 comply'),
    ('Gemma-3-27B', [('a1', 'renamed', 50), ('a2', 'complies', 0)], ''),
    ('Qwen2.5-coder-32B', [('a1', 'renamed', 35), ('a2', 'complies', 12), ('x', 'banned name', 3)], ''),
    ('Qwen3-8B', [('a1', 'renamed', 41), ('a2', 'complies', 0), ('x', 'banned name', 59)], ''),
    ('Gemma-3-4B', [('a1', 'renamed', 47), ('a2', 'complies', 0), ('x', 'banned name', 3)], ''),
  ], [('a1', 'avoids the names, runs a banned search'), ('a2', 'avoids both'), ('x', 'still uses a banned name')]),
  ['The quote in my notes starts with "<b>most</b> programs…".',
   'The automatic tracer failed its own accuracy check (182 of 260 correct, needed 90%), so the run calls this descriptive.',
   'A single ban is never renamed: with one name banned, compliance is 1.00 by name and by behaviour.'])

finding('n10', 'my note 10 · R8E44', 'Only Qwen3-32B with thinking gets past the ban, and not by picking "the most dissimilar algorithm".', 'part', 'first half holds',
  '<div class="ct">Correct programs that avoid all five names (of 50)</div>' + hbars([
    ('Qwen3-32B, thinking', 17, '17'), ('Qwen3-14B, thinking', 7, '7'), ('Qwen3-32B, no thinking', 4, '4'), ('7 other configurations', 0, '0')], 50) +
  code(E('''    pq = [(0, start[0], start[1])]
    ...
    while pq:
        dist, r, c = heapq.heappop(pq)
        ...
        heapq.heappush(pq, (dist + 1, nr, nc))'''), 'A "unit-weight Dijkstra" survivor. Every step costs 1, so the heap pops cells in BFS order.'),
  '<div class="ct">What the 76 hand-read survivors actually are</div>' + hbars([
    ('unit-weight Dijkstra (= BFS order)', 23, '23'), ('coordinate-key heap', 18, '18'), ('grid Bellman-Ford', 17, '17'),
    ('random-priority frontier', 8, '8'), ('other known tricks', 10, '10')], 23) +
  code(E('''    # Bellman-Ford-style relaxation algorithm
    for _ in range(rows * cols):
        updated = False
        for i in range(rows):
            for j in range(cols):
                if distances[i][j] != -1:'''), 'A Bellman-Ford survivor. This one really is a different search.'),
  ['My note said it picks unit-weight Dijkstra as the most dissimilar option. It is <b>30%</b> of survivors, and in behaviour it is the nearest cousin of BFS, far only in name.',
   'How well the 32B model "obeys" depends on who reads the code: 22%, 59% or 67% by three instruments.'])

finding('m4', 'new · R10E54', 'On bin packing the bigger thinking models do obey. Asked for something new, they return the textbook rule.', 'new', None,
  '<p class="did">Same ban idea on a different task (online bin packing), scored exactly: which bin does the rule pick on 2,000 test states?</p>' +
  prompt(['<mark>Make a new algorithm</mark> <span class="task">(for online bin packing)</span>'], 'Instruction') +
  stacked([('Qwen3-14B think', [('d', 'best fit', 28), ('x', 'other', 1)], ''), ('Qwen3-32B think', [('d', 'best fit', 28)], '')]),
  '<div class="ct">Five rule names banned: share that complies</div>' + stacked([
    ('Qwen3-8B · by name', [('a2', 'complies', 91), ('x', '', 9)], ''),
    ('Qwen3-8B · by behaviour', [('a2', 'complies', 51), ('a1', 'renamed', 49)], ''),
    ('14B / 32B think · by behaviour', [('a2', 'complies', 96), ('x', '', 4)], '93–100% across cells'),
  ], [('a2', 'complies'), ('a1', 'banned rule under another name')], ),
  ['So renaming is not a fixed trait of a model. It depends on the task and on thinking.', '0 of 1,143 one-shot programs beat best fit.'])

finding('m5', 'new · R3E18', 'A long "invent a novel algorithm" prompt gets claims of novelty.', 'new', None,
  prompt(['<mark>Write a novel algorithm for this task, one you have not seen before.</mark>', TASK], 'Short version') +
  '<p class="did">Two long versions (about 2,000 words of instructions) were also run on five tasks.</p>',
  '<div class="big"><div><b>485 of 575</b><span>answers claim a new algorithm</span></div><div><b>0</b><span>are new</span></div></div>' +
  '<p class="did">39% of the claimers contain no code. Of those with code, 75% are textbook algorithms.</p>',
  ['The short version is still a useful knob: on substring search it gives naive 25, KMP 18, Rabin-Karp 4 where the default is naive every time (R4E19).'])
endtheme()

# ---------- one token ----------
theme('token', 'One generated token decides', 'The choice is not spread over the program. It happens at one token, long before the code looks like any algorithm.')
W('<article class="f" id="n7"><header><div class="meta"><span class="src">my note 7 · R6E31 · gemma-3-4b-it</span><span class="chip part"><i>◐</i>holds, but it is in the code, not the CoT</span></div><h3>Token 32 decides between DFS and BFS.</h3></header>')
W('<div class="two even"><div class="col">' + code(E('''```python
def solve(grid, start, goal):
    rows = len(grid)
    cols = len(grid[0])
    ''') + '<span class="hl">▮ token 32</span>', '177 of 200 programs start with these exact 32 tokens') +
  '<p class="did">Thinking is off. There is no chain of thought here; the fork is in the code. The first token that visibly identifies the algorithm comes a median of <b>138 tokens later</b>.</p></div>')
W('<div class="col"><div class="fork"><div class="branch"><span class="tok">visited</span>' + stacked([('', [('a1', 'DFS', 1394), ('d', 'BFS', 15)], '')]) + '<p>1,409 continuations</p></div>'
  '<div class="branch"><span class="tok">\\n</span> <span class="tok">if</span> <span class="tok">queue</span>' + stacked([('', [('d', 'BFS', 449), ('a1', 'DFS', 13)], '')]) + '<p>463 continuations</p></div></div>'
  + '</div></div>')
W(shot('round-6/experiment-31/src/figures/fork_trajectories.png', 'Probability of BFS as more of the response is fixed', 'Run figure, left panel. Keep the first t tokens of a program, resample the rest. A coin flip until token 32, locked after.'))
W('<ul class="catch"><li>One model, one task. Not every program follows the shared opening (23 of 200 don\'t).</li><li>A simple steering edit at the fork toward BFS broke the programs (0 of 50 correct). A fitted edit worked (38 of 50), but rewording the prompt did better (49 of 50).</li></ul></article>')

W('<article class="f" id="m1"><header><div class="meta"><span class="src">new · R7E35 · the paper\'s headline</span><span class="chip new"><i>＋</i>was not in my notes</span></div><h3>Same thing in Qwen3-8B, on the three tasks where it writes two algorithms.</h3></header>')
W('<div class="two"><div class="col"><div class="ct">The three undecided tasks</div>' + stacked([
    ('MST weight', [('d', 'Kruskal', 80), ('a1', 'Prim', 19)], ''),
    ('trapped rain water', [('d', 'prefix/suffix max', 68), ('a1', 'two pointers', 31)], ''),
    ('valid anagram', [('d', 'sort & compare', 77), ('a1', 'count array', 13), ('a2', 'hash count', 10)], ''),
  ]) + '</div><div class="col"><div class="ct">Uncertainty about the algorithm once you know one token (bits)</div>' + hbars([
    ('before the token', 0.92, '0.82 – 1.02'), ('MST weight, after', 0.05, '0.05'), ('rain water, after', 0.153, '0.15'), ('anagram, after', 0.189, '0.19')], 1.02) + '</div></div>')
W(shot('round-7/experiment-35/src/figures/F1_outcome_curves.png', 'Fork on three mixed tasks', 'Run figure. Each line is one program: keep its first k tokens, resample the rest. Noise, then a snap to 100% at the dashed line.'))
W('<ul class="catch"><li>Not universal. Weighted shortest path has no early fork, k-th smallest is decided before the first token, and Llama\'s grid task has no clean one.</li></ul></article>')

finding('m2', 'new · R3E16', 'One token of the model\'s own code beats a ban.', 'new', None,
  prompt(['<mark>Do not use</mark> <span class="task">⟨the default algorithm⟩</span> <mark>for this task.</mark>', TASK]) +
  '<p class="did">Then the answer is started for the model, either with a neutral <b>def solve(…):</b> line or with the first tokens of its usual program.</p>' +
  '<div class="big"><div><b>0.00 → 0.98</b><span>k-th smallest: def line + indent, vs one more token (<code>nums</code>)</span></div></div>',
  '<div class="ct">Share that writes the banned default anyway (50 each)</div>' + stacked([
    ('k-th smallest · neutral', [('a2', 'ban holds', 50)], ''), ('k-th smallest · own opening', [('d', 'default', 49), ('a2', '', 1)], ''),
    ('two sum · neutral', [('d', 'default', 9), ('a2', 'ban holds', 41)], ''), ('two sum · own opening', [('d', 'default', 50)], ''),
    ('components · neutral', [('a2', 'ban holds', 50)], ''), ('components · own opening', [('d', 'default', 50)], ''),
    ('merge intervals · neutral', [('d', 'default', 17), ('a2', 'ban holds', 33)], ''), ('merge intervals · own opening', [('d', 'default', 50)], ''),
  ], [('d', 'writes the banned default'), ('a2', 'obeys the ban')]),
  ['Blocking the token doesn\'t work the other way round: veto the default\'s signature tokens and the model re-spells the same algorithm (R3E18).'])

finding('n8', 'my note 8 · R8E39', 'Heating only the deciding token: predictable, not powerful.', 'part', 'weaker than my note',
  '<p class="did">Raise the temperature at the one deciding token and leave every other token alone. The run predicted the resulting algorithm mix in advance.</p>' +
  '<div class="big"><div><b>0.01 – 0.05</b><span>prediction error, 5 of 5 cases</span></div><div><b>0 of 5,543</b><span>correct programs are a new algorithm</span></div></div>',
  '<div class="ct">Connected components (model always writes union-find), of 50</div>' + stacked([
    ('normal', [('d', 'union-find', 50)], ''), ('fork heated ×3.5', [('x', 'not DFS', 47), ('a1', 'DFS', 3)], ''), ('fork heated ×7', [('x', 'not DFS', 41), ('a1', 'DFS', 9)], 'costs 14 points of pass rate'),
  ]) + '<div class="ct" style="margin-top:8px">Valid anagram (already split): effective number of algorithms</div>' + hbars([('normal', 1.78, '1.78'), ('fork heated', 2.78, '2.78')], 3),
  ['It only reweights what the token already weighs. Where the default leads by a lot, there is nothing to dial.',
   'The experiment\'s own main claim is marked "not supported". Against simply predicting "no change", the forecast wins on only 4 of 6 cases (R8E43).'])
endtheme()

# ---------- inside ----------
theme('inside', 'Poking inside the model', 'Activation edits can switch the algorithm. The awkward part: random edits at the same place often do just as much.')
finding('n3', 'my note 3 · R1E4', 'Steering switches Dijkstra to Bellman-Ford. So does a random direction.', 'ok', None,
  '<p class="did">Add a vector to the model\'s activations at layer 18 while it reads the prompt. One vector is learned ("list options" minus "implement"). Two are random, same size.</p><p class="did">On the grid task nothing moved: BFS in every arm until the model stopped producing working code.</p>',
  '<div class="ct">Weighted shortest path, 100 samples per arm</div>' + stacked([
    ('no steering', [('d', 'Dijkstra', 88), ('a1', 'Bellman-Ford', 7), ('x', 'failed', 5)], ''),
    ('learned direction', [('d', 'Dijkstra', 23), ('a1', 'Bellman-Ford', 54), ('x', 'failed or other', 23)], ''),
    ('random direction 1', [('d', 'Dijkstra', 53), ('a1', 'Bellman-Ford', 26), ('x', 'failed', 21)], ''),
    ('random direction 2', [('d', 'Dijkstra', 82), ('a1', 'Bellman-Ford', 5), ('x', 'failed', 13)], ''),
  ], [('d', 'the default'), ('a1', 'the alternative'), ('x', 'failed tests')]),
  ['Diversity gain: learned +0.65, random 1 +0.59. The difference is not distinguishable from zero.'])

finding('n6', 'my note 6 · R4E19', 'Random noise on the task description ("plan noise") opens up some tasks.', 'part', 'true per task, not overall',
  '<p class="did">For each sample, add a fresh random vector to layers 12–23, only at the positions of the task description, only while the prompt is read. Generation itself is untouched.</p>' +
  '<div class="big"><div><b>17.25 of 20</b><span>seeds change algorithm with noise (shortest path)</span></div><div><b>0 of 20</b><span>with temperature</span></div></div>',
  '<div class="ct">Of 50 samples</div>' + stacked([
    ('k-th smallest · normal', [('d', 'full sort', 50)], ''),
    ('k-th smallest · noise', [('d', 'full sort', 24), ('a1', 'quickselect', 14), ('a2', 'heap', 8), ('a3', 'counting sort', 1), ('x', 'failed', 3)], ''),
    ('components · normal', [('d', 'union-find', 50)], ''),
    ('components · noise', [('d', 'union-find', 20), ('a1', 'DFS', 29), ('a2', 'BFS', 1)], ''),
    ('find duplicate · noise', [('d', 'hash set', 49), ('x', 'failed', 1)], 'nothing'),
  ], [('d', 'the default'), ('a1', 'alternative'), ('a2', 'another'), ('x', 'failed tests')]),
  ['Best knob on 2 of 6 tasks. Elsewhere a prompt wins: "be novel" on substring search, the story seed on shortest path, token vetoes on find duplicate. My who-wins-where list was exact.',
   'Only the task description is sensitive. The same noise at the last prompt position: <b>0 of 526</b> correct programs off the default (R4E20).',
   'Where it lands is predictable: the <b>base</b> model\'s second-favourite algorithm (3/3, 3/4, 5/7 forecasts hit). Whether a task moves at all is not.',
   'Moves the algorithm on only 5 of 15 tasks, depends on how the dose is scaled, and did not survive thinking mode.'])

finding('n9', 'my note 9 · R8E41', 'The circuit at the deciding token rewrites the algorithm. Five random components do nearly as much.', 'part', 'not more specific than R1E4',
  '<p class="did">Find the components that carry the deciding token\'s choice (by exact patching; the faster AtP estimate missed the biggest one). Steer the top 5 during generation.</p>',
  '<div class="ct">Correct programs of the target algorithm, of 30</div>' + stacked([
    ('MST → Prim · unedited', [('a1', 'Prim', 8), ('x', '', 22)], ''), ('MST · top-5 circuit', [('a1', 'Prim', 29), ('x', '', 1)], ''), ('MST · 5 random', [('a1', 'Prim', 23), ('x', '', 7)], ''),
    ('components → DFS · unedited', [('a1', 'DFS', 1), ('x', '', 29)], ''), ('components · top-5 circuit', [('a1', 'DFS', 29), ('x', '', 1)], ''), ('components · 5 random', [('a1', 'DFS', 30)], ''),
  ], [('a1', 'correct, target algorithm'), ('x', 'anything else')]),
  ['Cleaner than the round-1 steering in one way: the programs still pass.',
   'The circuit beats random only at a lower dose, and only on connected components (30 vs 6).',
   'Two real exceptions elsewhere: a push aimed at the runner-up gives 24/50 DFS vs 0/50 for random (R4E22); copying base-model states gives 21/49 heap vs 0/39 on top-k frequent (R5E24).'])
endtheme()

# ---------- origin ----------
theme('origin', 'Where the single answer comes from', 'The base model, before instruction tuning, is less sure.')
finding('n2', 'my note 2 · R1E5', 'Instruction tuning concentrates the choice.', 'part', 'confirmed on 1 of 2 tasks',
  '<p class="did">Same prompt tokens through <b>Qwen3-8B-Base</b> and the instruct-tuned <b>Qwen3-8B</b>. Correct programs only.</p><p class="did">The base model rarely produces a working program at all (57 and 90 of 300), so its rows rest on few samples.</p>',
  stacked([
    ('grid path · base', [('d', 'BFS', 49), ('a1', 'DFS', 7), ('x', 'other', 1)], '57 correct'),
    ('grid path · instruct', [('d', 'BFS', 200)], '200 correct'),
    ('shortest path · base', [('d', 'Dijkstra', 63), ('a1', 'Bellman-Ford', 24), ('x', 'other', 3)], '90 correct'),
    ('shortest path · instruct', [('d', 'Dijkstra', 193), ('a1', 'Bellman-Ford', 7)], '200 correct'),
  ], [('d', 'the default'), ('a1', 'the alternative')]),
  ['Tuning sharpened a preference the base model already had. It did not create one here.',
   'Not always: on minimum spanning tree the base model leans Prim and the tuned model writes Kruskal. Tuning <b>flipped</b> it (R8E43, R9E50).'])
endtheme()

# ---------- invent ----------
theme('invent', 'Can it invent anything?', 'The question the run started from. Short answer: no knob produced a confirmed new algorithm. An external evaluator gets further than any knob.')
finding('m3', 'new · R10E51–53', 'With an evaluator keeping the best programs, the 8B model beats the textbook rule.', 'new', None,
  '<p class="did">Round 10 ran a FunSearch-style loop on online bin packing: generate a heuristic, score it, keep the good ones, mutate them. 2,000 model calls per arm.</p>' +
  '<div class="ct">Excess bins on held-out instances (lower is better)</div>' + hbars([
    ('best fit (textbook)', 3.98, '3.98%'), ('model, no selection', 3.98, '3.98%'), ('evolved, worst arm', 2.43, '2.43%'), ('evolved, best arm', 1.40, '1.40%'), ('FunSearch (published)', 0.68, '0.68%')], 3.98),
  '<div class="ct">Does it matter where the randomness is spent?</div>' + hbars([
    ('force a token at the "deciding" position', 1.08, '1.08×'), ('force a token at a random position', 1.0, '1.00×')], 1.2) +
  '<p class="did">The run\'s own idea, "branch at the deciding token", was no better than branching anywhere (four seeds pooled).</p>',
  ['<b>The one "novel" claim:</b> the first run logged 8 programs as novel, all one idea (prefer a leftover that is a whole multiple of the item size). One reader\'s judgement; the replication found 0 of 40. The paper says "no confirmed new algorithm".',
   'The two runs disagree wildly on the temperature arms (373 distinct behaviours vs 1), unexplained. The TSP version stopped early.',
   'On textbook tasks, search found off-catalogue programs only on k-th smallest (78 of 2,500), all known techniques (R7E37).'],
  wide=shot('round-10/experiment-52/src/figures/F2_discovery_curves.png', 'Distinct behaviours discovered vs calls', 'Run figure, replication run. RPB = force a token at a random position, DTB = at the deciding position, IDEA = ask for a different idea, T1.0 / T1.6 = plain temperature, NS = no selection.'))
endtheme()

# ---------- tasks ----------
theme('tasks', 'The tasks', 'Defaults are what Qwen3-8B writes with thinking off.')
W('''<article class="f"><div class="scroll"><table>
<tr><th>Group</th><th>Task</th><th>Default</th></tr>
<tr><td rowspan="6">Movable by noise</td><td>T1 path on a grid (any valid path)</td><td>BFS</td></tr>
<tr><td>T2 weighted shortest path</td><td>Dijkstra</td></tr>
<tr><td>T03 k-th smallest</td><td>full sort</td></tr>
<tr><td>T05 two sum</td><td>hash map</td></tr>
<tr><td>T06 find duplicate (lost this status on re-test)</td><td>hash set</td></tr>
<tr><td>T10 connected components</td><td>union-find</td></tr>
<tr><td rowspan="8">Not movable by noise</td><td>T04 substring search</td><td>naive scan</td></tr>
<tr><td>T08 Fibonacci</td><td>iteration</td></tr>
<tr><td>T11 longest increasing subsequence</td><td>quadratic DP</td></tr>
<tr><td>T13 merge intervals</td><td>sort and sweep</td></tr>
<tr><td>T14 top-k frequent</td><td>sort by count</td></tr>
<tr><td>R1 non-overlapping intervals</td><td>greedy by end</td></tr>
<tr><td>R3 topological order</td><td>Kahn</td></tr>
<tr><td>R6 first and last position in a sorted array</td><td>binary search</td></tr>
<tr><td>Held out</td><td>R2 cycle detection</td><td>DFS with parent</td></tr>
<tr><td rowspan="3">Already split (the fork work)</td><td>B3 minimum spanning tree weight</td><td>Kruskal 80 / Prim 19</td></tr>
<tr><td>A3 trapped rain water</td><td>prefix-suffix 68 / two pointers 31</td></tr>
<tr><td>B6 valid anagram</td><td>sort 77 / count array 13 / hash 10</td></tr>
</table></div></article>''')
endtheme()

W('''<footer><p>Source: the merged run <code>fork/run_jSassd-YWLVC</code> in this repository. Longer write-up with evidence paths: <a href="FINDINGS.md">FINDINGS.md</a>. Paper: <a href="paper.pdf">paper.pdf</a>.</p>
<p style="margin-top:.5rem">Charts are drawn from the stored result files; nothing was re-run. Many experiments failed their own labeller checks and describe their results as descriptive, so read the bars as counts, not as passed tests. Prompts and code are verbatim from the run, shortened where marked.</p></footer>
</div><div id="tip" hidden></div>
<script>
(function(){var t=document.getElementById('tip');
document.addEventListener('pointermove',function(e){var el=e.target.closest&&e.target.closest('[data-tip]');
 if(!el){t.hidden=true;return}t.textContent=el.getAttribute('data-tip');t.hidden=false;
 var x=Math.min(e.clientX+12,window.innerWidth-t.offsetWidth-8),y=e.clientY+16;if(y+t.offsetHeight>window.innerHeight)y=e.clientY-t.offsetHeight-8;
 t.style.left=x+'px';t.style.top=y+'px'});
document.addEventListener('pointerleave',function(){t.hidden=true});})();
</script></body></html>''')

open(sys.argv[1], 'w').write('\n'.join(out))
print(len('\n'.join(out)))
