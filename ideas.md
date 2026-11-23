creativity manifold - empty space - 2d umap back to activation space - steer - new algorithm

fork tokens = few tokens decide the final algorithm
 -> most tokens high confidence - split at low confidence and unroll - map full tree  (fork token prob. = algorithm design prob.)

(base model list all possibilities - subagents implement each)
 (vs instruct "list all with probabilities" - from some paper)
 
 
 
 
SURE      = 0.90   # tuned top-1 above this: no decision here, keep walking
MIN_P     = 0.03   # base-model probability needed to become a branch
K         = 5      # max branches per position
R         = 5      # rollouts per branch
MAX_FORKS = 3      # max real forks along one path
MIN_MASS  = 1e-4   # stop exploring below this path probability

explore(prefix, mass, forks):
    # 1. walk while the tuned model is sure
    while tuned.top1_prob(prefix) >= SURE:
        prefix += tuned.top1(prefix)
        if finished(prefix): save_leaf(prefix, mass); return

    # 2. hesitation point: the base model proposes the options
    cands = base.top_tokens(prefix, k=K, min_prob=MIN_P) + [tuned.top1(prefix)]

    # 3. test each option: let the tuned model finish it R times
    for tok in cands:
        result[tok] = [label(tuned.sample(prefix + tok)) for _ in range(R)]

    # 4. wording or real fork?
    if every option leads to the same algorithm:
        prefix += tuned.top1(prefix); go to step 1          # wording only

    # 5. real fork: merge options with the same outcome, follow one per group
    for group in group_by_outcome(cands, result):
        tok = most_probable(group)
        m   = mass * sum(base_prob(t) for t in group)
        if   all R rollouts agree: save_leaf(prefix + tok, m)        # settled
        elif m > MIN_MASS and forks < MAX_FORKS:
            explore(prefix + tok, m, forks + 1)                      # still open




┌───────────────────────────────────────────────────────┬───────────────────────────────────────────────────┬────────────────────────────────────┐
│                     What you give                     │           Roughly how much you supplied           │          Who did the work          │
├───────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼────────────────────────────────────┤
│ Nothing; it's the default                             │ 0                                                 │ Model                              │
├───────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼────────────────────────────────────┤
│ Nothing; it's a rare branch in the tree with          │ log2(1/p) bits: you had to pick it out of many    │ Mostly model                       │
│ probability p                                         │ samples                                           │                                    │
├───────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼────────────────────────────────────┤
│ "It starts with H"                                    │ a couple of bits                                  │ Model                              │
├───────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼────────────────────────────────────┤
│ The full name, one of ~40                             │ about 5 bits                                      │ Model: a name is tiny next to the  │
│                                                       │                                                   │ code                               │
├───────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼────────────────────────────────────┤
│ "Try reversing the queue"                             │ a short sentence                                  │ Shared                             │
├───────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼────────────────────────────────────┤
│ Two ideas, "join them"                                │ the two descriptions                              │ Shared; the joining is the model's │
├───────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼────────────────────────────────────┤
│ Pseudo-code                                           │ most of it                                        │ Mostly you                         │
├───────────────────────────────────────────────────────┼───────────────────────────────────────────────────┼────────────────────────────────────┤
│ The whole algorithm                                   │ all of it                                         │ You; it's a copy test              │
└───────────────────────────────────────────────────────┴───────────────────────────────────────────────────┴────────────────────────────────────┘

Internals go on the same axis

Boosting an activation counts as help, and the question is how much information went into choosing the boost.

- A random direction, or one of a few dozen neurons: a few bits, like a first-letter hint. The knowledge was in the model.
- A direction fitted on examples of the target algorithm, or a vector optimised until the target comes out: that can carry the whole answer. It is the same as telling it.





What is creativity? Its not global - "make something new that nobody has ever done". Its more local - "come up with something that you have not seen before". - So that the question becomes, what do you know, and what is new to you? And only once we map that, we can start to measure your "creativity".

Three additions to make that measurable:
- "Seen before" can't be checked (no access to training data), so "knows" = what it produces with almost no help (unprompted, listing, a bare name).
- New is not enough: it must also work, and be more than a trivial variation (renamed variables, changed constant).
- Measure the two under different conditions, or it's circular: knowledge with cheap help, creativity with effort that carries no information about the answer (thinking, trial and error, a scoring loop).
