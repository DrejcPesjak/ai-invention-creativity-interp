# Actionable insights: how to get a different solution out of a code LLM

What to actually *do* with the results of this run. Written to be read on its own; the evidence behind each line is in [FINDINGS.md](FINDINGS.md).

**Where this comes from:** small open models (mostly Qwen3-8B, some Qwen3-14B/32B, Gemma-3-4b, Llama-3.1-8B) asked to write a Python function for a textbook task (find a path on a grid, shortest path, k-th smallest number, ...). For each answer we looked at *which algorithm* the code implements. So treat everything below as "worked on small models and textbook coding tasks", not as a law.

## The one thing to understand

Ask the model the same coding task 100 times and you get the same algorithm ~100 times (BFS for a grid path: 797 of 800). It is not that the model doesn't know the others. It writes DFS 0 times in 50 when left alone and 50 times in 50 when the prompt merely mentions DFS.

**So the model knows many solutions but always picks the same one.** Getting variety is a problem of *choosing*, and the choice is not touched by the usual randomness knobs.

## What does not work

| You try | What you get |
|---|---|
| Regenerate / change the random seed | The same algorithm with different variable names and comments |
| Raise the temperature | More ways of *wording* the same algorithm (3–4 phrasings become 24–36, the idea count stays at 1), until the code breaks |
| "Be creative", "invent a novel algorithm" | The default again, now described as novel. 485 of 575 answers claimed novelty; none were |
| A long "do not use A, B, C, D, E" list | Mostly the forbidden algorithms anyway, often under a different name |
| Add random words or a random string to the prompt | Nothing (0 to 1 point shift) |

## What works

**1. Say which approach you want. A mention is enough.**
You don't have to order it. "DFS is one well-known approach to this task; implement any correct algorithm" gave DFS 50 of 50 (unprompted: 0).
- It is not guaranteed: 2 of 9 mentioned algorithms hit 100%, others landed at 86%, 72%, 56%, 10%, and three at 0%.
- The code is worse than the default: the mentioned DFS was written 50 of 50 times but only 15 of 50 passed the tests. Always run it.

**2. Don't know the name? Describe how it works.**
A short story that implies the mechanism ("news spreads through the network in rounds...") moved shortest-path answers from Dijkstra to Bellman-Ford in 61 of 100. This one was less stable when repeated in later experiments, so it is a thing to try, not a sure thing.

**3. Forbid exactly one thing to get the model's second choice.**
"Do not use BFS" gave DFS 86 of 100. "Do not use Dijkstra" gave Bellman-Ford 83 of 100.
- Only one. With five forbidden names, 0 of 100 complied.
- The exact wording matters a lot (one phrasing dropped it to 30%), and it depends on the task: of 12 further tasks, only 5 obeyed a single ban at all.
- You can't chain it to walk through all the options: forbidding the first and the second together already falls apart on the path tasks.

**4. Write the first line of the answer yourself.**
The beginning of the code beats any instruction. If the answer is forced to start the way the default solution starts, a ban that normally works is ignored 98–100% of the time; on one task a *single* extra token made that difference. Turned around: if you can prefill the opening line of the approach you want, that is the strongest steer available.
- Corollary: if you paste existing code and ask for a different approach, the model tends to continue in the style already on the page.

**5. Turn thinking on if you need the model to actually obey a restriction.**
The bigger models with reasoning enabled followed bans in what the code does (93–100% on one task). Without thinking, the 8B model avoided the forbidden *words* 91% of the time and the forbidden *behaviour* only 51%.
- Thinking makes it obedient, not inventive: the same models asked to "make a new algorithm" returned the textbook one 28 of 29 and 28 of 28 times.

## Recipes for more diversity

These combine the points above. The first is the one I'd actually use.

**A. List first, then build each one separately.**
1. One call: "List the different approaches to this task." (The model knows 5–10 for a textbook task.)
2. One call *per approach*: "Implement approach X", ideally with the first line of code prefilled.
3. Run every result against tests.

Step 3 is not optional, because a named request ends in one of three ways:

| Outcome | Example from the run |
|---|---|
| Written and correct | most common algorithms |
| Written but broken | iterative-deepening DFS: 0 of 10 passed |
| Quietly replaced by a relative | asked for bidirectional Dijkstra, got plain Dijkstra 10 of 10 |

As a side effect you get a table of what the model can really do versus what it can only name. *The pieces were each measured; the three-step pipeline as a whole was not.*

**B. Let a different, less polished model propose the idea.**
The chat-tuned model has a much sharper favourite than the raw base model it was trained from (base Qwen wrote Bellman-Ford in 24 of 90 correct shortest-path programs; the tuned one almost never). A one-sentence plan written by the base model and handed to the tuned model gave 2.5 different algorithms on one task, against 1.1 for the fancy activation-level method. Practical version: use a second model (or a base model) to write the one-line plan, and your main model to write the code.

**C. If you can see token probabilities: branch where the model hesitates.**
The algorithm is usually settled at one token early in the code, long before the code visibly looks like any algorithm (a median of 138 tokens earlier in one case). Find the first position where the top token is not near-certain and generate one continuation per alternative.
- Works well when the model is already undecided (a task with 2–3 natural solutions).
- Does little when it has one strong favourite: the alternatives are there, but with tiny probability, and forcing them tends to break the code.
- Deliberately adding randomness at that spot was no better for variety than ordinary temperature. Branch, don't heat.

**D. If you run the model yourself and have its base version: use the base model for one token.**
At the deciding token, take the next-token probabilities from the base model; everywhere else use the tuned model. On two tasks this gave a correct non-default algorithm in 17 and 18 of 30 programs (untouched: 0 and 1 of 30), with 29 of 30 still passing. Variety of the base model at the moment of choice, code quality of the tuned model for the rest. Two tasks only, so promising, not proven.

**E. For solutions that are actually better, not just different: score and keep the best.**
The only thing in the whole run that produced something better than the textbook answer was a loop: generate many candidates, measure them, keep the best, ask for variations of those. On bin packing the 8B model went from the textbook rule (3.98% wasted bins) to 1.4–2.4%. Without the scoring step the same model just returns the textbook rule. This needs a task where quality can be measured automatically.

## Things to keep in mind

- **Check what the code does, not what it says it does.** Names, comments and claims ("without BFS", "a novel approach") are nearly free for the model. Under a long ban list, most "compliant" programs were the forbidden algorithm with new names (294 of 371 were plain BFS or DFS).
- **A list of forbidden things is also a list of suggestions.** One prompt that banned five named algorithms got one of those five back in 50 of 50 answers.
- **Show an example and the model copies it; forbid the example and it goes back to its default,** not to something new (24 of 31 cases).
- **A different algorithm is usually a worse-written one.** Expect lower pass rates off the default.
- **The model can tell you it's breaking the rule.** With thinking on, the reasoning named the forbidden algorithm in 91–100% of the programs that secretly used it (one ends: "I'll proceed with the BFS code, assuming the restriction is a mistake"). Reading the reasoning is a cheap check.

## What we did not find

- **No way to get a genuinely new algorithm from a single answer.** Across more than 20,000 checked programs, no prompt, temperature, ban, or internal intervention produced one. Every knob only moves the model between algorithms that are already in textbooks.
- **No internal "algorithm switch".** Pushing the model's internal activations in a carefully chosen direction changed the algorithm, but a random push usually did about as well. Nothing here beats a well-worded prompt.
- **No rule for which tasks can be moved.** Some tasks switch easily, some never do, and we couldn't predict which.

## If you only remember three things

1. Regenerating gives you the same idea in other words. To get another idea you have to ask for it by name or by description.
2. For real variety: list the approaches, request each one separately, test them all.
3. For something better than the textbook: you need a score and a loop, not a cleverer prompt.
