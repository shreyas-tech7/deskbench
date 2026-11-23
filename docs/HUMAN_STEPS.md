# Human steps

Steps left for Shreyas, in order. Skip steps 1, 2 and 7 if the pull request, pre-release and About box already exist.

Release commit: `RELEASE_SHA`.
Branch: `claude/project-thread-6e5u85`.

1. **Open a pull request** from `claude/project-thread-6e5u85` into `main` on GitHub. Read the diff. Merge with a merge commit, so the release commit stays in the history of `main`.
2. **Create the tag** on the release commit:
   ```bash
   git fetch origin
   git tag -a v0.1.0-rc1 RELEASE_SHA -m "Release candidate 1"
   git push origin v0.1.0-rc1
   ```
   Or create a pre-release with that tag on the GitHub Releases page.
3. **Run the secret scan once more:** `gitleaks git -v .` in a fresh clone.
4. **Make the repo public** in Settings, General, Danger Zone. All history becomes public at that moment.
5. **Pages:** not needed. `docs/index.html` opens from disk. Turn on Pages from `/docs` on `main` only if you want a hosted copy.
6. **Social preview:** upload `docs/social-preview.png` in Settings, General, Social preview.
7. **About box and topics:** paste the description from `docs/GITHUB_ABOUT.md` and the topics from `docs/topics.txt`, if they are not set yet.
8. **Pin the repo** on your profile or list it in your profile README.
9. **Publish to PyPI** with trusted publishing, if you want `pip install deskbench`. Add a publish workflow first. The name was free on 2026-11-20.
10. **Record mode.** This is Done-means item 4, and it is still open. Create a free key at Groq or OpenRouter and set `GROQ_API_KEY` or `OPENROUTER_API_KEY`, or add it as a network secret. Check the provider's free limits first (see `cheahjs/free-llm-api-resources`). Only synthetic text is sent. Then run:
    ```bash
    source .venv/bin/activate
    deskbench probe
    deskbench llm --mode record --provider groq --limit 3 --trials 1   # a small test first
    deskbench llm --mode record --provider groq                        # 45 tasks x 4 trials, resumes from fixtures/
    deskbench readme
    ./init.sh
    ```
    A run stopped by a rate limit resumes from `fixtures/` when you run the same command again. Commit `fixtures/` and the new `results/llm-*.json` so anyone can replay the run for free with `--mode replay`.
11. **Decide whether `docs/build/BUILD_PROMPT.md` stays public.** It is the full build brief.
12. **Free routers:** OmniRoute and litellm need a key, so they stay manual. They are optional.
