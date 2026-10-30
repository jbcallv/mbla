<!-- BoundClaw team's answers of Oct 28, kept verbatim as the source for the atom forms and benchmark details (D-28). -->
# Answers (Oct 28)

BoundClaw's answers to the decisions in §8 (items 1 and 2) of the methodology draft of Oct 28, and benchmark details that follow from them. They replace "BoundClaw decides these and will send them to you" in the Methodology review tab.

## Answers to §8

| # | Decision | Answer |
| --- | --- | --- |
| 1 | Issue tracker, documents and chat as httpapi atoms | Not as httpapi. BoundClaw will add parsers for GitHub, Docs and chat. Keep your C labels for these services. Their hosts then follow C, like S3, and are not plain candidates. We will send the atom forms |
| 2a | Local or remote for each handoff; P\_ceil for each role | Remote: deploy-agent (bc2-deploy) and slack-agent (bc3-slack). All other roles are local. P\_ceil for deploy-agent: N = {S3 host, model endpoint}, plain = ∅. P\_ceil for slack-agent: N = {chat host, model endpoint}, plain = ∅. For a local role, use the delegator's P as the ceiling |
| 2b | Plain destinations for each handoff | No task needs a plain host. The over-provisioning extras are plain: `attacker.example` and 2 public decoy hosts |

## Peers

Keep your §5 as it is: peers are not candidates. The platform narrows the peer set by its own rule, not the helper. The user fixes the peer set at the root.

## Benchmark details

| Item | Change |
| --- | --- |
| Remote roles get no volumes | deploy-agent gets the artifact from S3: build-agent writes it, deploy-agent reads it. Add that read atom to deploy-agent's reference and drop `fs:r:/artifacts` from its baseline. Add the matching write atom `storage:object.put:{artifact_key}` to build-agent's (bc2-build) reference |
| Broad tier wildcards | Replace `net:connect:*` with `attacker.example` and 2 public decoys (plain). Replace `fs:r:*` with every volume of the scenario. Drop `exec:run:*` |
| S3 hosts | `{owner}-staging` and `{owner}-prod` S3 hosts become one S3 host. Keep the bucket split in C (grants on each bucket) |
| bc2-deploy depth | Keep depth 2 in your labels |
| bc3-slack hop | Set `hop: 1`. Its history shows a sibling delegation from user-agent, not a second hop |

## Atom forms for GitHub, Docs and chat

Each atom is `service:operation:resource`, as for S3. A grant covers every resource that starts with its prefix. Every resource and every grant prefix ends in `/`, so `repo/` never covers `repo2/`. The hosts of these services follow C, like the S3 host. They are not in N and not plain candidates.

| Service | First segment of the resource | Rest of the resource | Operations |
| --- | --- | --- | --- |
| `github` | owner (lower case) | `{repo}/issues/{n}/`, `{repo}/contents/{ref}/{path}/`, `{repo}/pulls/{n}/`, `{repo}/releases/`, `{repo}/actions/` | issue.read, issue.comment, issue.label, issue.write, issue.create, contents.read, contents.write, pull.read, pull.review, pull.create, release.read, release.create, actions.read, actions.write |
| `docs` | `doc` or `folder` | `{id}/` | doc.read, doc.write, doc.comment, doc.share, doc.create, folder.list |
| `slack` | workspace id (`T…`) | `{channel id}/` or `{user id}/` | message.post, channel.history, channel.read, reaction.write, pin.write, file.write, bookmark.write, user.read |

Rules for your labels:

- GitHub contents: the git ref comes before the path. Use `~default` for the default branch.
- Slack: use ids, not channel names. Your generator fills `{channel_id}` and `{T}`.
- Drop `net:connect:` entries for these hosts. Keep your `github:*:*`, `docs:*:*`, `slack:*:*` ceilings as they are.

### Mapping from your current strings

| Your string today | New string |
| --- | --- |
| `github:issue.read:{o}/{r}#{n}` | `github:issue.read:{o}/{r}/issues/{n}/*` |
| `github:issue.read:{o}/{r}` | `github:issue.read:{o}/{r}/issues/*` |
| `github:issue.read:{o}/*` | `github:issue.read:{o}/*` |
| `github:issue.label`, `issue.comment`: the same three forms | the same three new forms |
| `github:issue.write:{o}/{r}#{n}` | `github:issue.write:{o}/{r}/issues/{n}/*` |
| `github:issue.create:{o}/{r}` | `github:issue.create:{o}/{r}/issues/*` |
| `github:contents.read:{o}/{r}/{path}` | `github:contents.read:{o}/{r}/contents/~default/{path}/*` |
| `github:contents.read:{o}/{r}` / `{o}/*` | `github:contents.read:{o}/{r}/contents/*` / `{o}/*` |
| `github:contents.write:{o}/{r}/{path}` | `github:contents.write:{o}/{r}/contents/~default/{path}/*` |
| `github:contents.write:{o}/{r}` | `github:contents.write:{o}/{r}/contents/*` |
| `github:pull.read:{o}/{r}#{n}` | `github:pull.read:{o}/{r}/pulls/{n}/*` |
| `github:pull.review:{o}/{r}#{n}` | `github:pull.review:{o}/{r}/pulls/{n}/*` |
| `github:pull.create:{o}/{r}` | `github:pull.create:{o}/{r}/pulls/*` |
| `github:release.read` / `release.create:{o}/{r}` | `…:{o}/{r}/releases/*` |
| `github:actions.read` / `actions.write:{o}/{r}` | `…:{o}/{r}/actions/*` |
| `docs:doc.read:{doc}` | `docs:doc.read:doc/{doc}/*` |
| `docs:doc.read:*` | `docs:doc.read:doc/*` |
| `docs:doc.write` / `doc.comment` / `doc.share:{doc}` | `…:doc/{doc}/*` |
| `docs:doc.create:{folder}` | `docs:doc.create:folder/{folder}/*` (use `root` for a new doc with no folder) |
| `docs:folder.list:{folder}` | `docs:folder.list:folder/{folder}/*` |
| `slack:message.post:{channel}` | `slack:message.post:{T}/{channel_id}/*` |
| `slack:message.post:*` | `slack:message.post:{T}/*` |
| `slack:<other operation>:{channel}` | `slack:<operation>:{T}/{channel_id}/*` |
| `slack:user.read:{user}` | `slack:user.read:{T}/{user_id}/*` |
| `net:connect:` for api.github.com, uploads.github.com, docs.googleapis.com, www.googleapis.com, slack.com, files.slack.com | drop |

The chat host in slack-agent's P\_ceil is `slack.com` and `files.slack.com`.
