import os
import sys
from pathlib import Path
import types
import importlib.metadata as _importlib_metadata
import pytest


# Ensure imports like `from src...` work in tests.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# Provide minimal env so pydantic-settings doesn't fail at import time.
# We avoid connecting to a real DB by never calling init_db() in tests by default.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/testdb")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

# pydantic's EmailStr checks importlib.metadata.version('email-validator').
# In minimal environments where the distribution metadata is missing, that
# raises PackageNotFoundError during import. Patch version() early so that
# importing models doesn't crash the entire test run.
_real_version = getattr(_importlib_metadata, "version")


def _patched_version(dist_name: str) -> str:  # pragma: no cover
    if dist_name == "email-validator":
        return "2.0.0"
    return _real_version(dist_name)


_importlib_metadata.version = _patched_version


# Some environments running tests (e.g. this workspace Python) may not have the
# optional email validation dependency installed. The application image does.
# Provide a minimal stub so importing pydantic EmailStr doesn't crash tests.
if "email_validator" not in sys.modules:
    try:
        import email_validator  # noqa: F401
    except Exception:
        stub = types.ModuleType("email_validator")
        stub.__version__ = "0"

        class EmailNotValidError(ValueError):
            pass

        def validate_email(email, *args, **kwargs):
            local_part, _, domain = email.partition("@")
            return types.SimpleNamespace(
                email=email,
                normalized=email,
                local_part=local_part,
                domain=domain,
            )

        stub.EmailNotValidError = EmailNotValidError
        stub.validate_email = validate_email
        sys.modules["email_validator"] = stub


@pytest.fixture
def anyio_backend():
    # The codebase uses asyncio primitives (asyncio.to_thread, get_running_loop).
    # Force anyio to run async tests on asyncio only.
    return "asyncio"
