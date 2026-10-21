"""Failure injection against real serialized models and the publication boundary."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ml import anomaly_detector as ad
from ml import common


@pytest.fixture
def training(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(ad.ml_settings, "ANOMALY_MIN_POINTS", 10)
    monkeypatch.setattr(ad.ml_settings, "ANOMALY_N_ESTIMATORS", 8)
    timestamps = [datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=i) for i in range(20)]
    features = np.arange(80, dtype=float).reshape(20, 4)
    monkeypatch.setattr(ad, "_load_features", lambda *args, **kwargs: (timestamps, features))
    return tmp_path


@pytest.mark.parametrize("project", ["legacy", "project-a"])
def test_checked_model_replaces_previous_only_at_publication(training, monkeypatch, project):
    path = common.model_path("anomaly", "orders", project)
    ad.train("orders", project)
    previous = path.read_bytes()
    original_replace = Path.replace
    publications = []

    def replace(candidate, destination):
        assert destination == path
        assert candidate.parent == path.parent
        assert candidate != path
        assert path.read_bytes() == previous
        assert isinstance(joblib.load(path)["model"], IsolationForest)
        artifact = joblib.load(candidate)
        assert set(artifact) == {"model", "scaler", "trained_at", "n_points"}
        assert artifact["n_points"] == 20
        publications.append(candidate)
        return original_replace(candidate, destination)

    monkeypatch.setattr(Path, "replace", replace)
    metadata = ad.train("orders", project)
    assert len(publications) == 1
    assert joblib.load(path)["trained_at"] == metadata["trained_at"]
    assert len(ad.score_table("orders", project_id=project)) == 20
    assert list(training.iterdir()) == [path]


@pytest.mark.parametrize("existing", [False, True], ids=["cold-start", "existing-model"])
@pytest.mark.parametrize("failure", ["partial-write", "flush", "load", "structure", "replace"])
def test_failure_preserves_working_model_and_removes_temporary_file(
    training, monkeypatch, existing, failure
):
    path = common.model_path("anomaly", "orders", "project-a")
    if existing:
        ad.train("orders", "project-a")
        previous = path.read_bytes()
        scores = ad.score_table("orders", project_id="project-a")
    original_dump = joblib.dump

    def fail(*args, **kwargs):
        raise OSError("injected persistence failure")

    def partial_write(payload, output):
        output.write(b"incomplete joblib file")
        fail()

    with monkeypatch.context() as injection:
        if failure == "partial-write":
            injection.setattr(ad._joblib, "dump", partial_write)
        elif failure == "flush":
            injection.setattr(ad.os, "fsync", fail)
        elif failure == "load":
            injection.setattr(ad._joblib, "load", fail)
        elif failure == "structure":
            injection.setattr(ad._joblib, "dump", lambda payload, out: original_dump({}, out))
        else:
            injection.setattr(Path, "replace", fail)
        with pytest.raises((OSError, ValueError)):
            ad.train("orders", "project-a")

    if existing:
        assert path.read_bytes() == previous
        assert ad.score_table("orders", project_id="project-a") == scores
        assert list(training.iterdir()) == [path]
    else:
        assert not path.exists()
        assert list(training.iterdir()) == []


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        {"model": "not a model"},
        {"scaler": "not a scaler"},
        {"model": IsolationForest()},
        {"scaler": StandardScaler()},
        {"scaler": StandardScaler().fit([[1, 2], [3, 4]])},
        {"n_points": True},
        {"n_points": 0},
        {"trained_at": None},
        {"trained_at": "not a timestamp"},
    ],
)
def test_invalid_serialized_contract_is_never_published(training, monkeypatch, invalid):
    ad.train("orders")
    path = common.model_path("anomaly", "orders")
    previous = path.read_bytes()
    original_dump = joblib.dump

    def corrupt(payload, output):
        return original_dump(None if invalid is None else {**payload, **invalid}, output)

    monkeypatch.setattr(ad._joblib, "dump", corrupt)
    with pytest.raises(ValueError):
        ad.train("orders")
    assert path.read_bytes() == previous
    assert joblib.load(path)["n_points"] == 20
    assert list(training.iterdir()) == [path]


def test_retrain_counts_persistence_failure_and_continues(training, monkeypatch):
    original_dump = joblib.dump

    def fail_first_table(payload, output):
        if "broken__anomaly" in output.name:
            output.write(b"partial")
            raise OSError("disk write failed")
        return original_dump(payload, output)

    monkeypatch.setattr(ad._joblib, "dump", fail_first_table)
    counts = ad.retrain_all(project_id="project-a", tables=["broken", "healthy"])
    assert counts == {"trained": 1, "skipped": 0, "errors": 1}
    healthy = common.model_path("anomaly", "healthy", "project-a")
    assert joblib.load(healthy)["n_points"] == 20
    assert list(training.iterdir()) == [healthy]
