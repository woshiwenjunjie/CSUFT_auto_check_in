from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "auto_checkin.sh"


def test_auto_checkin_script_does_not_import_nonexistent_scf_package():
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "deploy.tencent_scf" not in content


def test_auto_checkin_script_starts_with_plain_shebang():
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert content.startswith("#!/bin/bash")
