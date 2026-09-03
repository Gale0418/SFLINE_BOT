---
name: science-vault-quiz
description: Harden a LINE science QA bot with deterministic help commands, fixed-source quiz content, secure Postback state, bounded asynchronous webhook handling, and evidence-based review.
---

# Science Vault Quiz

Use this skill when adding a quiz, challenge, study or assessment mode to a LINE Messaging API bot without sacrificing webhook reliability or answer integrity.

## Core Principle

```text
verify raw signature
→ acknowledge quickly through a bounded queue
→ route deterministic product commands
→ keep quiz truth in a reviewed fixed bank
→ use signed state-bearing Postbacks
→ explain every answer
→ test all state transitions and failure boundaries
```

Do not ask an LLM to invent the correct answer during a live quiz. Models may help draft candidate questions offline, but a human-reviewed fixed answer and explanation must be the runtime source of truth.

## Workflow

1. **Ground the existing bot.** Read webhook, reply, memory, configuration, tests and deployment entry points before changing code.
2. **Define deterministic commands.** Help, challenge, rules, score and quit should use a normalized exact alias table. Do not use substring routing that steals ordinary questions.
3. **Design the character as stateful behavior.** Keep baseline identity stable; use a situation trigger for challenge voice. Avoid repetitive catchphrases and user-agency assumptions.
4. **Specify the bank.** Require unique IDs, one best answer, four plausible options, a causal explanation, a primary or authoritative source, and a stable fact horizon.
5. **Balance the bank.** Check domains, difficulties and answer positions. Balance is a regression signal, not proof of educational quality.
6. **Protect Postbacks.** Bind session ID, question ID, choice and a hashed user key with HMAC. Reject tampering, cross-user use, replay and expired sessions.
7. **Bound state.** Set TTL and capacity for quiz sessions, conversation memory, dedupe entries and workers.
8. **Preserve event order.** Same-conversation work must be FIFO; different conversations may run concurrently.
9. **Respect LINE limits.** Quick Reply ≤13 items, labels ≤20 characters, postback data ≤300 characters and text ≤5000 characters.
10. **Separate evidence.** Unit tests, offline bank validation, GitHub CI, physical-phone E2E and paid-model evaluation are different evidence classes.

## Review Gates

The minimum gate is:

```bash
python -m pip check
python -m compileall -q src tests
python -m pytest --cov=eternal_polaris --cov-branch --cov-report=term-missing
```

Also simulate every vault/difficulty path and explicitly test:

- duplicate webhook delivery
- full queue atomic rejection
- same-user rapid answers
- cross-user token use
- changed answer letter
- previous-question replay
- expiration and quit
- model outage while Help and Quiz remain available

Use `docs/quiz-strict-review-prompt.md` for the final adversarial pass.

## Guardrails

- Never claim asynchronous worker failure will be redelivered merely because dedupe state was cleared after a 200 ACK.
- Never retry a network-ambiguous Reply API call without a provider-supported idempotency mechanism.
- Never mix fixed quiz accuracy with free-form model classification metrics.
- Never treat an official homepage as proof that every detailed statement in a question is supported; source at the narrowest practical level.
- Never add leaderboards, accounts, Rich Menu, RPG inventory or adaptive difficulty before the core five-question path and physical-phone acceptance are stable.

## Definition of Done

A quiz upgrade is done only when:

- the bank loads under strict schema validation;
- every supported route completes;
- all signed-state attacks fail safely;
- Help and Quiz work without model access;
- the webhook remains bounded and fast to acknowledge;
- tests pass from a clean install;
- unresolved external acceptance steps are stated honestly.
