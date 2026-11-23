# Prompt for Claude Cowork

Paste everything below the line into Claude Cowork.

---

You are helping Shreyas finish the GitHub repo `shreyas-tech7/deskbench`. Do not ask questions. Do not stop without a result. Work in the browser on github.com only.

Rules:

- Do not make the repo public.
- Do not publish a package, enter any key or token, sign in for Shreyas, or pay for anything.
- Every step below is free and can be undone.

Steps:

1. Open the Actions tab of the repo. Report the status of the latest CI run on `main` and on `claude/project-thread-6e5u85`. If a run failed, copy the failing step name and its last 20 log lines.
2. Open the repo home page. Check the About box. If the description is empty, set it to the text in `docs/GITHUB_ABOUT.md`. If the topics are empty, add the topics from `docs/topics.txt`.
3. Open Settings, General, Social preview. Upload `docs/social-preview.png` from the repo (download it from the file page first).
4. Open the Releases page. Report whether a `v0.1.0-rc1` pre-release exists and which commit it points to.

When you finish, write the next prompt for Claude Code. It must hold:

- The context: deskbench is a benchmark for customer-support agents on small-business policies, v0.1.0-rc1, branch `claude/project-thread-6e5u85`.
- What is complete: the steps above that worked, with what you saw.
- What is open: the steps that failed, and the human steps left in `docs/HUMAN_STEPS.md` (public repo, PyPI, the record-mode key and run).
- This launcher, word for word: "Read docs/build/BUILD_PROMPT.md and follow it. Resume from PROGRESS.md on branch claude/project-thread-6e5u85. Do not ask questions. Do not stop until every Done-means item is true or blocked with a fallback."
