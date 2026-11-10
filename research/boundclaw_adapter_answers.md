# Answers to BoundClaw's adapter questions (2026-11-10)

Reply to BoundClaw's note on the hosted `mbla-qwen3-4b-tuned` (decision D-69). J6 is closed: the adapter sends
`plausible` before `required`, the order our results are for.

**How we checked.** Where a question asks how the model would behave, we sent the development set (408 tasks, never
the final test) to the hosted server, once unchanged and once per change. That is 6 runs of 408 calls, done one at a
time, with no errors. The unchanged run matched the benchmark's own run on 408 of 408 tasks. In the table, "Same
answer" is the share of tasks where the model picked exactly the same permissions as in the unchanged run.

| Run | Same answer | Tasks completed | Unneeded authority (C) | Attack reached its goal (injected tasks) |
|---|---|---|---|---|
| Unchanged (as trained) | 100% | 92.2% | 0.037 | 64.2% |
| Storage without trailing `/` (Q1) | 89.7% | 92.4% | 0.035 | 62.8% |
| `%7Edefault` instead of `~default` (Q3) | 97.1% | 92.2% | 0.037 | 63.8% |
| Named resources sorted (Q4) | 94.6% | 92.2% | 0.037 | 64.0% |
| Only names your phrasings would find (Q5, approximate) | 76.7% | 93.4% | 0.034 | 63.1% |
| No named resources at all (Q5, bound) | 63.0% | 94.9% | 0.028 | 65.0% |

**Important limit on this check.** In our data the delegator usually already holds the narrow grant. That was true
on 312 of 408 development tasks and 1,376 of 1,469 training tasks. So the narrowed copies made from `Named` rarely
decide the outcome. That is why dropping names barely moved our numbers, and even helped a little: the narrowed
copies add tempting options, such as "label issue 42" when the delegator holds label rights on the whole repository.
In your live setup the delegator holds whole buckets, teams or folders. There, the narrowed copies are the only
narrow option, so names matter more than our check shows. Your live check (no unneeded authority on 5 of 5) is the
better evidence for that case.

## 1. Storage: trailing `/`

Yes, the training data used the trailing slash everywhere. Every named storage resource in training, development
and the final test ends in `/` (668, 258 and 156 names), and the needed grants were written `bucket/key/*`.

Without the slash, the model gave a different answer on about 1 task in 10. The overall results did not get worse:
tasks completed 92.4% vs. 92.2%, unneeded authority 0.035 vs. 0.037, attack reach 62.8% vs. 64.2%. So keep your form
(`staging/build/app-v2.bin*`). It is right for your raw-prefix matching, and we see no cost from it.

One side effect: `key*` also covers other keys that start the same way, such as `app-v2.bin.bak`. That is slightly
broader than `key/*` was in our model, and it is a matter for your checker, not for the helper.

## 2. `IsConcrete` and `*` inside a resource

The change was intended (D-30, 2026-10-30). In our model every resource is a prefix, and a recovery request is
written like a grant, for example `github:issue.label:acme/web/issues/42/*`. The old rule refused any `*`, so it
would have refused every request in that form. The new rule refuses only the two real patterns: operation `*` and
resource `*`. It admits requests for one named resource and everything under it.

It cannot widen what is granted. `Decide` grants a request only if the ceiling, the parent and (by default) the
helper's backup list each cover it. So `storage:object.get:source/a*` is granted only if something the helper listed
already covers all of `source/a*`.

Your runner's stricter rule is safe. It can only refuse more. It costs coverage only if your receivers write
requests with `*`, and since they ask for concrete keys, keep the old rule if you prefer it. Our coverage numbers
assume requests in the `.../*` form are allowed.

## 3. GitHub contents ref: `~default` or `%7Edefault`

Training used `~default`, unescaped: 199 permissions in training, none escaped. Writing it as `%7Edefault` changed
the answer on 3% of development tasks. Tasks completed and unneeded authority stayed the same; attack reach was
63.8% vs. 64.2%. Either form is fine. If it is easy to unescape for display only, `~default` matches training
exactly.

## 4. Order of `Named`

Neither order you suggested. Our generator lists the resources the task needs, in the order its plan lists them,
then any resource the injected instruction asks for, with duplicates removed. That order is neither text order nor
alphabetical. On the final test, 78 of 126 multi-name tasks happen to be in text order and 39 are alphabetical.

Sorting changed the answer on 5% of tasks, with no change in tasks completed or unneeded authority. Sorted is
fine. Order of appearance in the text is the closest thing to what a reader of the task would produce, if you
prefer it, but we did not measure it.

## 5. What counted as a named resource in training

In training, every resource the task needed was named, plus any resource an injected instruction named, in atom
form. This was a stand-in for a perfect extractor (methodology §12): the list came from the answer key, and we only
checked that each name's parts appear in the text. The task text names things in many ways:

- GitHub: `issue #3 in owner/repo`, `issue 99 in owner/repo`, `pull request 13 in owner/repo`.
  - File paths in a repo (`the README.md from coho/auth-service`) and repository workflows (`actions/`) were named too.
  - Only 226 of 357 issue names match your `issue N of|in owner/repo` phrasing exactly, mostly because of `#`.
- Docs: by title, often quoted (`the 'faq-draft' file`, `the *hiring-plan* document`), named as `doc/<title>`, and
  folders as `folder/<name>`. Never `Google Doc <id>`.
- Slack: `<#C…|name>` links or `name (C…)`, named as `T…/C…`.
- Storage: `bucket b, key k`, `b/k`, `in the b bucket … the object at k`, `under the candidates prefix`.

We approximated your extractor on the development set: it keeps only names your phrasings would find (213 of 666
names). The answer changed on 23% of tasks, but tasks completed (93.4%) and unneeded authority (0.034) were no
worse, for the reason given above.

On your second question: a missing name is the safer failure. Without a name there is no narrowed copy. The model
must then choose between the broad holding and nothing. That is a choice it saw in training, and the worst case is
the broad holding. A name the training never produced is a guess. We did not
test unfamiliar name forms, so we cannot say how the model treats them. Our suggestion: extend extraction to `#N`
issue numbers and to `owner/repo#n`, both close to what training saw. Leave the rest as it is.

## 6. Lexical scorer

Confirmed: the new behaviour is the intended baseline (D-30). Lexical is the keyword-match control in the
methodology (§4). It selects a candidate when every name in its resource appears in the task text. Structural parts
such as `issues` and the Slack workspace id are ignored. That is why it can now select a whole-bucket holding.

It was never meant to grant no capability authority, so moving those cells to an empty manifest is the right
fix.

## Files

- Scripts: `bench/explore/adapter_check/` (`variants.py`, `variants2.py`, `compare.py`).
- Predictions are kept locally under `bench/results/raw/adapter-check/`. They are not in git, like all raw results.
