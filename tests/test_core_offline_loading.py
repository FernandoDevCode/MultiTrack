from dataclasses import replace
from pathlib import Path

import pytest

from stemlab.app import SIX_STEMS
from stemlab.domain import BackendSeparationError
from stemlab.separation.audio_separator_adapter import Separator, _VerifiedLocalCoreSeparator


def test_core_resolves_only_approved_local_pair_without_online_discovery(tmp_path, monkeypatch):
    monkeypatch.setattr(Separator, "__init__", lambda self, **kw: None)

    def no_catalog(*args, **kwargs):
        raise AssertionError("Offline Core attempted model discovery/download")

    monkeypatch.setattr(Separator, "download_file_if_not_exists", no_catalog)
    model = SIX_STEMS.model_spec(tmp_path)
    separator = _VerifiedLocalCoreSeparator(model=model)
    resolved = separator.download_model_files(model.checkpoint_path.name)
    assert resolved[1] == "MDXC"
    assert Path(resolved[3]) == model.checkpoint_path
    assert Path(resolved[4]) == model.config_paths[0]
    assert not separator.model_is_uvr_vip
    with pytest.raises(ValueError, match="allowlisted"):
        separator.download_model_files("arbitrary.ckpt")


@pytest.mark.parametrize("change", [
    {"expected_sha256": "a" * 64},
    {"expected_config_sha256": ("b" * 64,)},
    {"model_id": "arbitrary"},
])
def test_core_rejects_unapproved_spec_before_runtime_initialization(tmp_path, monkeypatch, change):
    def no_initialization(*args, **kwargs):
        raise AssertionError("Unapproved Core spec reached model runtime")

    monkeypatch.setattr(Separator, "__init__", no_initialization)
    with pytest.raises(BackendSeparationError, match="approved local artifacts"):
        _VerifiedLocalCoreSeparator(model=replace(SIX_STEMS.model_spec(tmp_path), **change))
