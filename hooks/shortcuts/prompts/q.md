The user prefixed `q:` — they asked a question and want the answer stored in `./.claude/artifacts/Q&A.md` for later reference.

First, answer the question normally in this session.

Then append a Q&A entry to `{dst}` (newest first; the file already has the `# Q&A` header) using one Edit/Write call:

## {today YYYY-MM-DD} — {≤8-word topic}
**Q:** {question, `q:` stripped}
**A:** {1–3 sentence summary of your answer}

<details><summary>full reply</summary>

{your full answer above, verbatim}

</details>

Skip if exact duplicate of the latest entry.
