# Code Review: v0.8.2 UTC 时间规范化 + GPS 自动重试 + 通知美化

**Date:** 2026-06-09
**Base SHA:** 5f2812b
**Head SHA:** 824c036
**Reviewer:** AI Code Reviewer (subagent)

---

## Strengths

1. **All 31 tests pass** — Solid test coverage for crypto, sign, geo, config, and cross-validation
2. **Clean architecture** — Clear separation: `ApiClient` handles all 8 API endpoints with unified auth/signature/retry; CLI commands delegate to it
3. **Security done right** — Credentials masked in output (`_mask`), passwords obfuscated in config (`$obf:<base64>`), no hardcoded secrets
4. **Documentation sync** — CHANGELOG, memory doc (014), AGENTS.md all updated per convention
5. **UTC time handling fixed** — Server uses UTC; notifications now show "13:00–14:30 UTC (北京时间 21:00–22:30)" everywhere; workflow comment clarified
6. **WebVPN mode added** — `client_mode` parameter cleanly switches credentials, Referer, User-Agent; new `login-webvpn` command for token-based auth
7. **GPS auto-retry** — Halves offset up to 5 attempts instead of failing immediately; removes false-alarm notifications

---

## Issues

### Important (Should Fix)

| File | Issue | Why It Matters | Fix |
|------|-------|----------------|-----|
| `src/utils/sign.py:16-28` | Global state mutation in `set_client_credentials` | If multiple `ApiClient` instances with different modes are created in same process, last one wins. CLI is single-threaded so currently safe, but fragile for future reuse (e.g., FastAPI multi-user). | Make `CLIENT_ID/SECRET` instance attributes on `ApiClient`; pass to `generate_sign`/`generate_basic_auth` as args. |
| `scripts/cli_commands/auth.py:140` | Loose token validation: `tasks.get("success") or tasks.get("code") == 200 or tasks.get("data")` | Accepts responses that may not actually be valid (e.g., error response with `data` field). Server response structure should be validated strictly. | Check `tasks.get("success") is True` or `tasks.get("code") == 200` only; add unit test for WebVPN login flow. |
| `scripts/auto_checkin.sh:199-200` | Shell script parses CLI Chinese output (`grep -qE "打卡成功"`) | Couples shell script to CLI language; if CLI output changes (e.g., i18n), workflow breaks. | Use the existing `CHECKIN_RESULT: status=... date=...` machine-readable line for all decisions (already extracted at line 182-189). |

### Minor (Nice to Have)

| File | Issue | Suggestion |
|------|-------|------------|
| `scripts/cli_commands/checkin.py:100-111` | GPS retry has no minimum offset floor | Add `if cur_offset < 1e-6: break` to avoid infinite halving if dorm itself is outside range (unlikely but safe). |
| `docs/guides/user/CLI教程.md` | Not updated for `login-webvpn` command | Add WebVPN login instructions and `client_mode` config explanation. |
| `docs/guides/user/fiddler-抓包获取OpenID.md` | Should mention WebVPN alternative | Note that `login-webvpn` avoids OpenID capture entirely. |
| `src/core/client.py:35` | `client_mode` default `"wxapp"` not validated | Add `assert client_mode in ("wxapp", "web")` or raise `ValueError`. |

---

## Recommendations

1. **Refactor sign.py to avoid globals** — Pass credentials explicitly; enables true multi-tenant support for Phase 3 (FastAPI multi-user).
2. **Add WebVPN integration test** — Mock `get_task_list` response to verify `login-webvpn` saves config with `client_mode: "web"`.
3. **Use `CHECKIN_RESULT` line in shell script** — Replace all `grep "中文"` checks with `parse_result_field` for robustness.
4. **Consider structured logging** — CLI could output JSON (`--json` flag) for shell script consumption, decoupling completely.

---

## Assessment

**Ready to merge?** Yes (with fixes for the two Important items)

**Reasoning:** The implementation correctly delivers all planned v0.8.2 features: UTC normalization, GPS auto-retry, notification polish, and WebVPN login. Architecture is sound, all 31 tests pass, and documentation is synchronized. The global-state mutation in `sign.py` and loose validation in `auth.py` are the only substantive risks — both are localized and fixable without redesign.