"""Readiness failure logging must not leak database credentials or mask actual 503 responses."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from backend.app.errors import ServiceError
from backend.app.main import readiness


def test_readiness_database_failure_emits_safe_classification():
    secret = "DO_NOT_LOG_THIS_M18_DB_SECRET"

    class FailingSession:
        def execute(self, statement):
            _ = statement
            raise OperationalError("secret URL " + secret, {}, RuntimeError(secret))

    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(model_ready=True)))
    with patch("backend.app.main.logging.getLogger") as logger_factory:
        with pytest.raises(ServiceError) as error:
            readiness(req, FailingSession())
    assert error.value.status_code == 503
    assert error.value.code == "DATABASE_UNAVAILABLE"
    call = logger_factory.return_value.warning.call_args
    assert "M18_READINESS_DB_FAILED" in call.args[0]
    assert "OperationalError" in call.args
    assert "RuntimeError" in call.args
    assert secret not in repr(call)


def test_readiness_model_failure_does_not_pretend_ready():
    class HealthySession:
        def execute(self, statement):
            _ = statement
            return None

    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(model_ready=False)))
    with patch("backend.app.main.logging.getLogger") as logger_factory:
        with pytest.raises(ServiceError) as error:
            readiness(req, HealthySession())
    assert error.value.status_code == 503
    assert error.value.code == "MODEL_UNAVAILABLE"
    call = logger_factory.return_value.warning.call_args
    assert "M18_READINESS_MODEL_FAILED" in call.args[0]
