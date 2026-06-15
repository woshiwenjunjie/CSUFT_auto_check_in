"""config sync — 将 config.json 同步到 password.txt 和 scf_env.json"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from scripts.cli_config import CONFIG_FILE
from scripts.cli_ui import Style, c, bullet


PASSWORD_FILE = Path("password.txt").resolve()
SCF_ENV_FILE = Path("deploy/tencent-scf/scf_env.json").resolve()


def _get_all_profiles() -> dict[str, dict[str, str]]:
    """读取 config.json 中的所有 profiles"""
    if not CONFIG_FILE.exists():
        return {}
    raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return raw.get("profiles", {})


def _sync_password_txt(profiles: dict[str, dict[str, str]]) -> bool:
    """更新 password.txt 中的 OpenID/username"""
    if not PASSWORD_FILE.exists():
        return False

    text = PASSWORD_FILE.read_text(encoding="utf-8")
    changed = False

    for name, data in profiles.items():
        oid = data.get("openid", "")
        uid = data.get("username", "")

        marker_oid = f"CHECKIN_OPENID_{name}="
        if oid:
            new_line = f"{marker_oid}{oid}"
            if marker_oid in text:
                start = text.index(marker_oid)
                end = text.index("\n", start)
                if text[start:end] != new_line:
                    text = text[:start] + new_line + text[end:]
                    changed = True
            else:
                marker_uid = f"CHECKIN_USERNAME_{name}="
                if marker_uid in text:
                    insert_at = text.index(marker_uid)
                    end_of_line = text.index("\n", insert_at)
                    text = text[:end_of_line+1] + new_line + "\n" + text[end_of_line+1:]
                    changed = True

        marker_uid = f"CHECKIN_USERNAME_{name}="
        if uid:
            new_line = f"{marker_uid}{uid}"
            if marker_uid in text:
                start = text.index(marker_uid)
                end = text.index("\n", start)
                if text[start:end] != new_line:
                    text = text[:start] + new_line + text[end:]
                    changed = True

    if changed:
        PASSWORD_FILE.write_text(text, encoding="utf-8")

    return changed


def _sync_scf_env(profiles: dict[str, dict[str, str]]) -> int:
    """生成/更新 scf_env.json"""
    if not SCF_ENV_FILE.parent.exists():
        return 0

    env = {}
    if SCF_ENV_FILE.exists():
        env = json.loads(SCF_ENV_FILE.read_text(encoding="utf-8"))

    profile_names = ",".join(
        p for p in sorted(profiles.keys())
        if profiles[p].get("openid") or profiles[p].get("username")
    )
    if profile_names:
        env["CHECKIN_PROFILES"] = profile_names

    for name in sorted(profiles.keys()):
        data = profiles[name]
        if data.get("openid"):
            env[f"CHECKIN_OPENID_{name}"] = data["openid"]
        if data.get("username"):
            env[f"CHECKIN_USERNAME_{name}"] = data["username"]

    SCF_ENV_FILE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(env)


def run(args: Namespace) -> None:
    """config sync 入口"""
    profiles = _get_all_profiles()

    if not profiles:
        print()
        bullet("没有找到任何 profile", ok=False)
        return

    print()
    bullet("同步配置到 password.txt ...")
    pw_ok = _sync_password_txt(profiles)
    if pw_ok:
        bullet("password.txt 已更新")
    else:
        bullet("password.txt 无变更或不存在", ok=False)

    print()
    bullet("重新生成 scf_env.json ...")
    n = _sync_scf_env(profiles)
    if n > 0:
        bullet(f"scf_env.json 已生成 ({n} 个变量)")
    else:
        bullet("deploy/tencent-scf/ 不存在，跳过", ok=False)

    print()
    bullet("同步完成")
