# Mission 18 — GitHub Actions 실제 실행·실패 원인

**Status (2026-10-11 KST): GitHub 원격 저장소/Push PASS, Hosted CI BLOCKED (account billing), CODE TESTS NOT STARTED.**

- Repository: https://github.com/exobiz7/mission18-movie-review-intelligence
- Visibility: **PRIVATE** (GitHub CLI actual `isPrivate=true`).
- Branch: `main`, initial pushed SHA: `7b399445facf5ae828b6014454877ee991c13e6d`, normal non-force push.
- Run: https://github.com/exobiz7/mission18-movie-review-intelligence/actions/runs/38114719687
- Run ID: `38114719687`
- Event: Push
- Created (UTC): 2026-10-11T05:25:12Z
- Conclusion: `failure`, completed in ~4 seconds.
- Job `contract-and-lint`: `failure`, **0 executed steps**, runner_name empty.
- Job `pinned-real-model-smoke`: `skipped` (dependent on failed job).
- Precise GitHub annotation:

> The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings

No script, dependency installer, pytest, model download or Python command executed in this GitHub-hosted run. **Do not attribute it to source code or mark CI PASS.** GitHub separately posted a non-blocking announcement about upcoming ubuntu-latest image migration.

## Owner-only resolution

1. Go to https://github.com/settings/billing while logged into the same GitHub account.
2. Inspect payment failures, account spending limits and GitHub Actions availability. Make changes to billing **only with the owner's deliberate approval**.
3. After access is restored, re-run a workflow from its Actions UI or push a new normal commit on `main`. Verify the job steps, actual checkout/uv/Python/pytest/G2/G3, the summary and commit SHA. Do not claim CI success based only on green local runs.
4. If billing is not to be modified, keep hosted CI **BLOCKED**. A privileged self-hosted runner on the general-purpose Mac Studio is **not recommended** without a separately provisioned, sandboxed, dedicated runner.

Reference sources: GitHub Actions run annotation (above), GitHub Actions settings API reported `enabled=true` and `allowed_actions=all`; the problem is billing/account entitlement, **not** repository Actions permission.
