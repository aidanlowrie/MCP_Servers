import json
from pathlib import Path
from types import SimpleNamespace

import pytest

# The functions we want to test
import server


class DummyCompletedProcess(SimpleNamespace):
    def __init__(self, stdout="[]"):
        super().__init__(stdout=stdout)

    def __iter__(self):
        return iter([])


def test_build_btt_url_with_secret(monkeypatch):
    monkeypatch.setenv("BTT_SHARED_SECRET", "xyz")
    url = server._build_btt_url("trigger_named", {"trigger_name": "Test"})
    assert "shared_secret=xyz" in url
    assert url.startswith("btt://trigger_named/?")


def test_add_btt_trigger_invokes_open(monkeypatch):
    calls = []

    def fake_run(cmd, check):
        calls.append(cmd)

    monkeypatch.setattr(server, "subprocess", SimpleNamespace(run=fake_run))
    server.add_btt_trigger(
        server.AddTriggerArgs(trigger_json='{"BTTDummy":"yes"}')
    )
    assert calls, "open() was never called"
    assert calls[0][0] == "open"
    assert calls[0][1].startswith("btt://add_new_trigger/")


def test_list_btt_triggers_parses_json(monkeypatch):
    sample_json = json.dumps(
        [{"BTTUUID": "123", "BTTAppBundleIdentifier": "com.apple.finder"}]
    )

    def fake_check_output(cmd, text):
        return sample_json

    monkeypatch.setattr(server, "subprocess", SimpleNamespace(check_output=fake_check_output))
    triggers = server.list_btt_triggers()
    assert triggers[0]["BTTUUID"] == "123"
