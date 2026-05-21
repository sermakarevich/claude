# fleet_of_agents

A tutorial that builds up to running a fleet of Claude coding agents in parallel — one capability per step. Stop at any step and you have a working setup. Start with a single agent that writes its work to disk; end with multiple parallel agents consuming a shared queue and asking you questions when stuck.

| Step | Adds | When to stop here |
|---|---|---|
| [Step 1 — materialize output](step_1_materialize_output/) | Agent writes task context (`TASK.md` / `PLAN_AND_PROGRESS.md` / `FINDINGS.md`) to `.claude/tasks/<task_id>/` so work survives across sessions. | One agent, manual driving, but every task is resumable. |
| [Step 2 — TODO/DONE queue](step_2_todo_done/) | On-disk queue: append to `TODO.md`, agent picks the top entry and logs to `DONE.md`. | You manage a backlog but still drive each iteration. |
| [Step 3 — loop.sh](step_3_loop/) | `./loop.sh` invokes `claude -p` repeatedly until the queue is empty. | One unattended agent chewing through your TODO. |
| [Step 4 — beads](step_4_beads/) | Replaces `TODO.md`/`DONE.md` with `bd`; the loop atomically claims tasks; multiple `./loop.sh` instances can run in parallel. | A fleet of parallel agents on a shared queue. |
| [Step 5 — Q&A blocking](step_5_qa_blocking/) | Agent can ask you a question (writes to `Q&A.md` + marks the task blocked); the loop skips blocked tasks until you answer. | A fleet that can stop and ask instead of guessing. |

