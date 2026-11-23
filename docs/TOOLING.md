# Tooling

Each tool below was vetted before use. Skills were scanned with cisco-ai-defense skill-scanner before they ran. The scan logs showed no high or medium findings for any of them.

| Tool | Source | Version | Why | Check |
| --- | --- | --- | --- | --- |
| superpowers skills | obra/superpowers, already in the session | session copy | plans, TDD, debugging, verification | used, nothing installed |
| ponytail, ponytail-review | DietrichGebert/ponytail | skills installed with `npx skills add` | least code, and the release review | skill-scanner: 0 findings for ponytail, 1 info for ponytail-review |
| caveman | JuliusBrussee/caveman | skill | terse progress chat only, never docs | skill-scanner: 1 info |
| humanizer | blader/humanizer | skill | docs polish before the release | skill-scanner: 1 low |
| gitleaks | github.com/zricethezav/gitleaks | version is set by build process | secret scan before commits and on history | installed with go install |
| actionlint | github.com/rhysd/actionlint | v1.7.12 | workflow lint | installed with go install |
| pip-audit | PyPI | pip-audit 2.10.1 | dependency audit | installed with uv tool |
| ruff | PyPI | ruff 0.17.6 | lint, format, `--select S` security rules | dev extra |
| skill-scanner | PyPI cisco-ai-skill-scanner | installed | scan new skills before use | used on the four skills above |
| graphify | PyPI graphifyy | not installed | code map for resume runs | skipped, the repo has under 30 source files |
| osv-scanner, semgrep | GitHub | not used | dependency and code scan | api.osv.dev and semgrep.dev are refused by the network here |
| LlamaFirewall, Prompt Guard, garak, mcp-scanner | GITHUB_REPOS.md | not used | prompt injection and MCP checks | do not fit: no model runs by default, no MCP server, and the models need huggingface.co |
| OmniRoute, litellm | GITHUB_REPOS.md | not used | free model routing | need a key, listed in `docs/HUMAN_STEPS.md` |
| crawl4ai, playwright-mcp, anatomy | GITHUB_REPOS.md | not used | crawling, UI tests, figure | no crawl, no UI, and the figure is a stretch goal |
| cheahjs/free-llm-api-resources | GITHUB_REPOS.md | read only | free limits before a record run | raw.githubusercontent.com redirected and no run happened, so it was not needed |

The project itself has no runtime dependencies. It uses only the Python standard library.
