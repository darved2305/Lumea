"""
Test helpers/fakes shared across pytest modules.
"""


class FakeScalars:
    def __init__(self, rows):
        self._rows = list(rows or [])

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


class FakeResult:
    """
    Emulates SQLAlchemy Result object used in codebase:
    - scalar_one_or_none()
    - scalars().all() / scalars().first()
    """

    def __init__(self, *, scalar=None, scalar_one_or_none=None, scalars_rows=None):
        self._scalar = scalar
        self._scalar_one_or_none = scalar_one_or_none
        self._scalars_rows = list(scalars_rows or [])

    def scalar(self):
        return self._scalar

    def scalar_one(self):
        if self._scalar_one_or_none is None:
            raise AssertionError("FakeResult.scalar_one called but no scalar_one_or_none configured")
        return self._scalar_one_or_none

    def scalar_one_or_none(self):
        return self._scalar_one_or_none

    def scalars(self):
        return FakeScalars(self._scalars_rows)


class FakeAsyncSession:
    """
    Minimal AsyncSession fake.

    Configure `execute_results` as a list; each `execute()` pops the next.
    """

    def __init__(self, execute_results=None):
        self._execute_results = list(execute_results or [])
        self.added = []
        self.commits = 0
        self.refreshed = []

    async def execute(self, stmt):
        if not self._execute_results:
            raise AssertionError("FakeAsyncSession.execute called more times than configured")
        return self._execute_results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)
