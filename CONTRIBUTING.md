# Contributing to EPSILON

EPSILON welcomes criticism before expansion. The most useful contribution is a result another person can inspect: a reproduction attempt, a methodological challenge, a failing test, or a correction.

## Choose a contribution path

- **Reproduce a fixed release:** use the Reproduction Report issue form. A mismatch and an inability to complete the procedure are both valid results.
- **Challenge the method:** use the Methodological Challenge issue form or [Falsification Challenge Discussion #8](https://github.com/DresdenGman/EPSILON-trading-simulator/discussions/8).
- **Fix code or documentation:** open an issue first when the change alters the evidence contract, data provenance, execution model, or public claims.

## Evidence standard

Please include:

1. the exact release, tag, or commit SHA;
2. your operating system and relevant runtime versions;
3. the command or public workflow you followed;
4. the observed result or failure;
5. the expected result and why;
6. an output file, artifact hash, log excerpt, or screenshot when useful.

Do not include API keys, passwords, private datasets, personal information, or brokerage credentials.

## Integrity rules

- Synthetic results must remain labeled synthetic.
- A sensitivity result is not a profitability, prediction, or general robustness claim.
- Negative and inconclusive results remain part of the public record.
- Do not solicit or coordinate Stars, votes, comments, or endorsements.
- Reviewers are quoted by name only with permission.

## Issue triage

Maintainers process incoming reports as follows:

1. **Label** — each report is labeled to match the form it came in through: `bug` for product defects, `documentation` for documentation corrections, `enhancement` for feature requests, `reproduction` for reproduction reports, and `methodology`/`external-review` for methodological challenges. A report that arrives on the wrong form is relabeled, not closed. Labels that do not exist in the repository are created before use so issue filters stay accurate.
2. **Confirm** — a maintainer reproduces the report or verifies the documentation claim before work begins. Reports that cannot be confirmed are left open with a request for the missing revision, environment, or reproduction detail, and closed only after the reporter is given a clear chance to provide it.
3. **Close** — a report is closed when the fix is merged and verified, when the described behavior is confirmed intentional and documented, or when the report is withdrawn. Every closure states the reason in a comment.
4. **Route** — reproduction mismatches stay on the Reproduction Report form and methodological objections stay on the Methodological Challenge form; product defects, documentation corrections, and feature requests use the forms added for them.

Sensitive content is handled as follows. Reporters must not include credentials, private datasets, personal information, or brokerage details. If credentials or secrets are exposed in a report or its attachments, maintainers ask the reporter to **revoke or rotate the affected credentials immediately**; editing or deleting the text does not invalidate a secret. Where possible, the offending comment or attachment is also removed or hidden, and the incident is noted in the issue so the exposure remains visible to the reporter and reviewers.

## Development checks

Before a pull request, run the relevant tests for the surface you changed. For the current web evidence instrument, the public acceptance criteria are a working no-login path, explicit provenance, a pre-specified rejection rule, and an exportable evidence artifact.
