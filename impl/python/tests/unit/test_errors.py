"""Unit tests for :mod:`osi.errors`.

Invariants (per ``ARCHITECTURE.md §7``):

1. Every raised exception in production code is an ``OSIError`` subclass
   with a stable code.
2. Tests assert on ``error.code``, never on message text. This file
   double-checks that assertion remains mechanically possible.
3. Every ``Exception`` subclass declared anywhere under ``osi.*`` is
   itself an ``OSIError`` (or explicitly allow-listed). The arch test
   below walks every loaded ``osi`` module and enforces this.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

import pytest

import osi
from osi.errors import (
    AlgebraError,
    ErrorCode,
    OSICodegenError,
    OSIError,
    OSIParseError,
    OSIPlanningError,
    OSIWarning,
)


class TestErrorCode:
    def test_codes_are_stable_strings(self) -> None:
        assert ErrorCode.E_DEFERRED_KEY_REJECTED.value == "E_DEFERRED_KEY_REJECTED"
        assert ErrorCode.E4001_EXPLOSION_UNSAFE.value == "E4001"
        assert ErrorCode.E5001_DIALECT_UNSUPPORTED.value == "E5001"

    def test_all_codes_have_correct_prefix(self) -> None:
        # Legacy numeric prefixes (E1xxx..E5xxx, W6xxx) coexist with the
        # Foundation v0.1 named family (E_*) during the rollout. The
        # named family is migrating in via S-1..S-17; both must remain
        # valid until S-17 (final compliance) deletes the last legacy
        # numeric code.
        prefixes = {"E1", "E2", "E3", "E4", "E5", "W6", "E_"}
        for code in ErrorCode:
            assert code.value[:2] in prefixes, f"bad prefix for {code}"

    def test_codes_are_unique(self) -> None:
        values = [code.value for code in ErrorCode]
        assert len(values) == len(set(values))


class TestOSIError:
    def test_carries_code_and_message(self) -> None:
        err = OSIError(ErrorCode.E1001_YAML_SYNTAX, "bad yaml")
        assert err.code is ErrorCode.E1001_YAML_SYNTAX
        assert "bad yaml" in str(err)

    def test_context_defaults_to_empty_dict(self) -> None:
        err = OSIError(ErrorCode.E1001_YAML_SYNTAX, "x")
        assert err.context == {}

    def test_context_is_copied_defensively(self) -> None:
        src = {"key": "value"}
        err = OSIError(ErrorCode.E1001_YAML_SYNTAX, "x", context=src)
        src["key"] = "mutated"
        assert err.context == {"key": "value"}

    @pytest.mark.parametrize(
        "cls",
        [OSIParseError, OSIPlanningError, AlgebraError, OSICodegenError, OSIWarning],
    )
    def test_subclasses_are_osi_errors(self, cls: type[OSIError]) -> None:
        err = cls(ErrorCode.E1001_YAML_SYNTAX, "x")
        assert isinstance(err, OSIError)
        assert err.code is ErrorCode.E1001_YAML_SYNTAX


# Allow-list of exception classes that are intentionally not ``OSIError``.
# This must stay empty unless there is a documented reason (e.g. an
# adapter-boundary translation class that wraps a third-party SDK error).
_NON_OSI_EXCEPTION_ALLOWLIST: frozenset[str] = frozenset()


def _walk_osi_exception_classes() -> list[type[BaseException]]:
    """Import every module under ``osi.*`` and return every Exception class.

    Only classes whose ``__module__`` starts with ``osi.`` are returned —
    re-exports of ``Exception``/``ValueError`` etc. are filtered out.
    ``__main__`` modules are skipped because importing them executes
    their CLI entry point.
    """
    seen: set[type[BaseException]] = set()
    package_path = osi.__path__
    for module_info in pkgutil.walk_packages(package_path, prefix="osi."):
        if module_info.name.endswith(".__main__"):
            continue
        try:
            module = importlib.import_module(module_info.name)
        except Exception:
            continue
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, BaseException):
                continue
            if not obj.__module__.startswith("osi."):
                continue
            seen.add(obj)
    return sorted(seen, key=lambda c: f"{c.__module__}.{c.__qualname__}")


class TestExceptionHierarchyInvariant:
    """Architecture test: every osi.* Exception is an OSIError.

    Regression guard for the Phase 8c finding that
    ``GrainSimulationError`` subclassed ``ValueError`` and slipped past
    the typed-error doctrine. Adding a new ``Exception`` subclass under
    ``osi.*`` is now a deliberate act: either inherit from ``OSIError``
    or add the fully qualified name to ``_NON_OSI_EXCEPTION_ALLOWLIST``
    with a comment explaining why.
    """

    def test_every_osi_exception_inherits_from_osi_error(self) -> None:
        violations: list[str] = []
        for cls in _walk_osi_exception_classes():
            qualname = f"{cls.__module__}.{cls.__qualname__}"
            if qualname in _NON_OSI_EXCEPTION_ALLOWLIST:
                continue
            if not issubclass(cls, OSIError):
                violations.append(qualname)
        assert not violations, (
            "These exception classes live under osi.* but do not inherit from "
            "OSIError. Either fix the inheritance or extend "
            "_NON_OSI_EXCEPTION_ALLOWLIST with rationale:\n  "
            + "\n  ".join(violations)
        )
