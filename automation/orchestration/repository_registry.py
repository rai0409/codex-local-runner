"""Strict, read-only Repository Registry contracts.

This module resolves source declarations and machine-local Profile bindings.  It
does not execute commands, mutate Git state, or authorize delivery actions.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

from automation.orchestration.repository_profile import RepositoryProfile
from automation.orchestration.repository_profile import RepositoryProfileValidationError
from automation.orchestration.repository_profile import load_repository_profile
from automation.orchestration.repository_profile import validate_repository_profile
from orchestrator.config_loader import load_yaml_file

REPOSITORY_REGISTRY_SCHEMA_VERSION = 1
REPOSITORY_BINDINGS_SCHEMA_VERSION = 1
REPOSITORY_RESOLUTION_STATUSES = (
    "resolved",
    "disabled",
    "unbound",
    "profile_missing",
    "profile_invalid",
    "profile_id_mismatch",
    "duplicate_repository_root",
)
DEFAULT_REPOSITORY_BINDINGS_PATH = "~/.config/codex-local-runner/repository-bindings.json"

_REGISTRY_FIELDS = frozenset(("version", "repos"))
_DECLARATION_FIELDS = frozenset(
    ("name", "logical_role", "enabled", "profile_id", "description")
)
_BINDINGS_FIELDS = frozenset(("version", "bindings"))
_BINDING_FIELDS = frozenset(("repository_id", "profile_path"))
_BUNDLE_FIELDS = frozenset(("registry", "bindings"))
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class RepositoryRegistryValidationError(ValueError):
    """Validation failure carrying a stable machine-readable reason code."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True)
class RepositoryDeclaration:
    name: str
    logical_role: str
    enabled: bool
    profile_id: str
    description: str


@dataclass(frozen=True)
class RepositoryBinding:
    repository_id: str
    profile_path: str


@dataclass(frozen=True)
class ResolvedRepository:
    declaration: RepositoryDeclaration
    binding: RepositoryBinding
    profile: RepositoryProfile


@dataclass(frozen=True)
class RepositoryResolution:
    repository_id: str
    status: str
    reason_code: str
    detail_reason_code: str | None
    declaration: RepositoryDeclaration
    binding: RepositoryBinding | None
    resolved_repository: ResolvedRepository | None


@dataclass(frozen=True)
class RepositoryRegistry:
    version: int
    declarations: tuple[RepositoryDeclaration, ...]
    bindings: tuple[RepositoryBinding, ...]


def _error(reason_code: str, message: str) -> RepositoryRegistryValidationError:
    return RepositoryRegistryValidationError(reason_code, message)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error(f"{path}.invalid_type", "must be an object")
    return value


def _strict(raw: Mapping[str, Any], fields: frozenset[str], path: str) -> None:
    unknown = sorted(str(key) for key in raw if key not in fields)
    if unknown:
        raise _error(f"{path}.{unknown[0]}.unknown_field", "unknown field")


def _required(raw: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in raw:
        raise _error(f"{path}.{key}.required", "is required")
    return raw[key]


def _single_line_text(value: Any, path: str, *, empty: bool = False) -> str:
    if not isinstance(value, str):
        raise _error(f"{path}.invalid_type", "must be a string")
    if "\0" in value or "\n" in value or "\r" in value:
        raise _error(f"{path}.invalid_value", "must be single-line text")
    if value.strip() != value or (not empty and not value):
        raise _error(f"{path}.invalid_value", "must be non-empty text without surrounding whitespace")
    return value


def _identifier(value: Any, path: str) -> str:
    text = _single_line_text(value, path)
    if not _IDENTIFIER.fullmatch(text):
        raise _error(f"{path}.invalid_value", "must be a repository identifier")
    return text


def _version(value: Any, path: str, expected: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(f"{path}.invalid_type", "must be an integer")
    if value != expected:
        raise _error(f"{path}.unsupported", f"must be {expected}")
    return value


def _declaration_mapping(item: RepositoryDeclaration) -> dict[str, Any]:
    return {
        "name": item.name,
        "logical_role": item.logical_role,
        "enabled": item.enabled,
        "profile_id": item.profile_id,
        "description": item.description,
    }


def _binding_mapping(item: RepositoryBinding) -> dict[str, Any]:
    return {"repository_id": item.repository_id, "profile_path": item.profile_path}


def _registry_mapping(registry: RepositoryRegistry) -> dict[str, Any]:
    return {
        "version": registry.version,
        "repos": [_declaration_mapping(item) for item in registry.declarations],
    }


def _bindings_mapping(bindings: tuple[RepositoryBinding, ...]) -> dict[str, Any]:
    return {
        "version": REPOSITORY_BINDINGS_SCHEMA_VERSION,
        "bindings": [_binding_mapping(item) for item in bindings],
    }


def _registry_instance_mapping(registry: RepositoryRegistry) -> dict[str, Any]:
    return {
        "registry": _registry_mapping(registry),
        "bindings": _bindings_mapping(registry.bindings),
    }


def _declarations(raw: Any) -> tuple[RepositoryDeclaration, ...]:
    source = _mapping(raw, "registry")
    _strict(source, _REGISTRY_FIELDS, "registry")
    version = _version(_required(source, "version", "registry"), "registry.version", REPOSITORY_REGISTRY_SCHEMA_VERSION)
    entries = _required(source, "repos", "registry")
    if not isinstance(entries, list):
        raise _error("registry.repos.invalid_type", "must be a list")
    if not entries:
        raise _error("registry.repos.empty", "must not be empty")
    declarations: list[RepositoryDeclaration] = []
    names: set[str] = set()
    profile_ids: set[str] = set()
    for index, raw_item in enumerate(entries):
        path = f"registry.repos[{index}]"
        item = _mapping(raw_item, path)
        _strict(item, _DECLARATION_FIELDS, path)
        name = _identifier(_required(item, "name", path), f"{path}.name")
        logical_role = _single_line_text(
            _required(item, "logical_role", path), f"{path}.logical_role"
        )
        enabled_value = item.get("enabled", True)
        if not isinstance(enabled_value, bool):
            raise _error(f"{path}.enabled.invalid_type", "must be a boolean")
        profile_id = _identifier(item.get("profile_id", name), f"{path}.profile_id")
        description = _single_line_text(
            item.get("description", ""), f"{path}.description", empty=True
        )
        if name in names:
            raise _error(f"{path}.name.duplicate", "duplicate repository name")
        if profile_id in profile_ids:
            raise _error(f"{path}.profile_id.duplicate", "duplicate Profile ID")
        names.add(name)
        profile_ids.add(profile_id)
        declarations.append(
            RepositoryDeclaration(name, logical_role, enabled_value, profile_id, description)
        )
    del version
    return tuple(sorted(declarations, key=lambda item: item.name))


def _base_directory(value: str | os.PathLike[str] | None) -> Path | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, os.PathLike)):
        raise _error("bindings.base_directory.invalid_type", "must be a path")
    text = os.fspath(value)
    if isinstance(text, bytes) or not text.strip():
        raise _error("bindings.base_directory.invalid_type", "must be a non-empty text path")
    candidate = Path(text).expanduser()
    if not candidate.exists():
        raise _error("bindings.base_directory.not_found", "does not exist")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_dir():
        raise _error("bindings.base_directory.not_directory", "must be a directory")
    return resolved


def _binding_path(value: Any, path: str, base_directory: Path | None) -> str:
    text = _single_line_text(value, path)
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        if base_directory is None:
            raise _error(f"{path}.relative_without_base", "requires a base directory")
        candidate = base_directory / candidate
    return str(candidate.resolve(strict=False))


def _binding_raw(value: Any, declarations: tuple[RepositoryDeclaration, ...], base_directory: Path | None) -> tuple[RepositoryBinding, ...]:
    raw = _mapping(value, "bindings")
    _strict(raw, _BINDINGS_FIELDS, "bindings")
    _version(_required(raw, "version", "bindings"), "bindings.version", REPOSITORY_BINDINGS_SCHEMA_VERSION)
    entries = _required(raw, "bindings", "bindings")
    if not isinstance(entries, list):
        raise _error("bindings.bindings.invalid_type", "must be a list")
    names = {item.name for item in declarations}
    seen: set[str] = set()
    bindings: list[RepositoryBinding] = []
    for index, raw_item in enumerate(entries):
        path = f"bindings.bindings[{index}]"
        item = _mapping(raw_item, path)
        _strict(item, _BINDING_FIELDS, path)
        repository_id = _identifier(
            _required(item, "repository_id", path), f"{path}.repository_id"
        )
        if repository_id in seen:
            raise _error(f"{path}.repository_id.duplicate", "duplicate repository binding")
        if repository_id not in names:
            raise _error(f"{path}.repository_id.unknown", "does not exist in the registry")
        seen.add(repository_id)
        bindings.append(
            RepositoryBinding(
                repository_id,
                _binding_path(_required(item, "profile_path", path), f"{path}.profile_path", base_directory),
            )
        )
    return tuple(sorted(bindings, key=lambda item: item.repository_id))


def validate_repository_bindings(
    bindings: Mapping[str, Any] | tuple[RepositoryBinding, ...] | list[RepositoryBinding],
    declarations: tuple[RepositoryDeclaration, ...] | list[RepositoryDeclaration],
    *,
    base_directory: str | os.PathLike[str] | None = None,
) -> tuple[RepositoryBinding, ...]:
    """Strictly validate local bindings; this never loads a bound Profile."""
    declaration_raw = [
        _declaration_mapping(item) if isinstance(item, RepositoryDeclaration) else item
        for item in declarations
    ]
    validated_declarations = _declarations(
        {"version": REPOSITORY_REGISTRY_SCHEMA_VERSION, "repos": declaration_raw}
    )
    normalized_base = _base_directory(base_directory)
    if isinstance(bindings, tuple) or isinstance(bindings, list):
        raw: Any = {
            "version": REPOSITORY_BINDINGS_SCHEMA_VERSION,
            "bindings": [
                _binding_mapping(item) if isinstance(item, RepositoryBinding) else item
                for item in bindings
            ],
        }
    else:
        raw = bindings
    return _binding_raw(raw, validated_declarations, normalized_base)


def validate_repository_registry(
    registry: Mapping[str, Any] | RepositoryRegistry,
    bindings: Mapping[str, Any] | tuple[RepositoryBinding, ...] | list[RepositoryBinding] | None = None,
    *,
    bindings_base_directory: str | os.PathLike[str] | None = None,
) -> RepositoryRegistry:
    """Strictly validate a Registry bundle without resolving Profiles."""
    if isinstance(registry, RepositoryRegistry):
        if bindings is not None:
            raise _error("registry_bundle.bindings_argument.conflict", "cannot supply bindings with a Registry instance")
        raw_registry: Any = _registry_instance_mapping(registry)
    else:
        raw_registry = registry
    root = _mapping(raw_registry, "registry")
    is_bundle = "registry" in root or "bindings" in root
    if is_bundle:
        _strict(root, _BUNDLE_FIELDS, "registry_bundle")
        if bindings is not None:
            raise _error("registry_bundle.bindings_argument.conflict", "bindings are already in the bundle")
        source = _required(root, "registry", "registry_bundle")
        binding_source = _required(root, "bindings", "registry_bundle")
    else:
        source = root
        binding_source = (
            {"version": REPOSITORY_BINDINGS_SCHEMA_VERSION, "bindings": []}
            if bindings is None
            else bindings
        )
    declarations = _declarations(source)
    validated_bindings = validate_repository_bindings(
        binding_source, declarations, base_directory=bindings_base_directory
    )
    return RepositoryRegistry(
        REPOSITORY_REGISTRY_SCHEMA_VERSION, declarations, validated_bindings
    )


def _load_path(value: str | os.PathLike[str], path: str) -> Path:
    if isinstance(value, bool) or not isinstance(value, (str, os.PathLike)):
        raise _error(f"{path}.invalid_type", "must be a text path")
    text = os.fspath(value)
    if isinstance(text, bytes) or not text.strip():
        raise _error(f"{path}.invalid_type", "must be a non-empty text path")
    candidate = Path(text).expanduser()
    if not candidate.exists():
        raise _error(f"{path}.not_found", "does not exist")
    if not candidate.is_file():
        raise _error(f"{path}.not_file", "must be a file")
    return candidate


def load_repository_bindings(
    binding_path: str | os.PathLike[str],
    declarations: tuple[RepositoryDeclaration, ...] | list[RepositoryDeclaration],
) -> tuple[RepositoryBinding, ...]:
    """Load one UTF-8 JSON binding file and strictly validate it."""
    path = _load_path(binding_path, "bindings_file")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise _error("bindings_file.read_failed", "is not UTF-8 text") from exc
    except OSError as exc:
        raise _error("bindings_file.read_failed", "could not be read") from exc
    except json.JSONDecodeError as exc:
        raise _error("bindings_file.json_invalid", "is not valid JSON") from exc
    if not isinstance(raw, Mapping):
        raise _error("bindings_file.root.invalid_type", "JSON root must be an object")
    return validate_repository_bindings(raw, declarations, base_directory=path.resolve().parent)


def load_repository_registry(
    registry_path: str | os.PathLike[str],
    binding_path: str | os.PathLike[str] | None = None,
) -> RepositoryRegistry:
    """Load a source registry and optional machine-local JSON bindings."""
    path = _load_path(registry_path, "registry_file")
    try:
        raw = load_yaml_file(path)
    except (OSError, UnicodeDecodeError) as exc:
        raise _error("registry_file.read_failed", "could not be read") from exc
    except Exception as exc:
        raise _error("registry_file.parse_failed", "could not be parsed") from exc
    if not isinstance(raw, Mapping):
        raise _error("registry_file.root.invalid_type", "root must be an object")
    declarations = _declarations(raw)
    loaded_bindings = (
        ()
        if binding_path is None
        else load_repository_bindings(binding_path, declarations)
    )
    return validate_repository_registry(
        {"version": REPOSITORY_REGISTRY_SCHEMA_VERSION, "repos": [_declaration_mapping(item) for item in declarations]},
        loaded_bindings,
    )


def _resolution(
    declaration: RepositoryDeclaration, binding: RepositoryBinding | None
) -> RepositoryResolution:
    prefix = f"registry.resolution[{declaration.name}]"
    if not declaration.enabled:
        return RepositoryResolution(
            declaration.name, "disabled", f"{prefix}.disabled", None, declaration, binding, None
        )
    if binding is None:
        return RepositoryResolution(
            declaration.name, "unbound", f"{prefix}.unbound", None, declaration, None, None
        )
    profile_path = Path(binding.profile_path)
    if not profile_path.exists() or not profile_path.is_file():
        detail = "profile_file.not_found" if not profile_path.exists() else "profile_file.not_file"
        return RepositoryResolution(
            declaration.name, "profile_missing", f"{prefix}.profile_missing", detail,
            declaration, binding, None,
        )
    try:
        profile = validate_repository_profile(load_repository_profile(profile_path))
    except RepositoryProfileValidationError as exc:
        return RepositoryResolution(
            declaration.name, "profile_invalid", f"{prefix}.profile_invalid",
            exc.reason_code, declaration, binding, None,
        )
    if profile.profile_id != declaration.profile_id:
        return RepositoryResolution(
            declaration.name, "profile_id_mismatch", f"{prefix}.profile_id_mismatch",
            None, declaration, binding, None,
        )
    return RepositoryResolution(
        declaration.name, "resolved", f"{prefix}.resolved", None, declaration, binding,
        ResolvedRepository(declaration, binding, profile),
    )


def list_repository_resolutions(
    registry: RepositoryRegistry,
) -> tuple[RepositoryResolution, ...]:
    """Classify each declaration deterministically without command or Git execution."""
    validated = validate_repository_registry(registry)
    bindings = {item.repository_id: item for item in validated.bindings}
    candidates = [
        _resolution(declaration, bindings.get(declaration.name))
        for declaration in validated.declarations
    ]
    roots: dict[str, list[int]] = {}
    for index, item in enumerate(candidates):
        if item.resolved_repository is not None:
            root = os.path.normcase(
                os.path.normpath(item.resolved_repository.profile.repository_root)
            )
            roots.setdefault(root, []).append(index)
    for indexes in roots.values():
        if len(indexes) > 1:
            for index in indexes:
                item = candidates[index]
                candidates[index] = RepositoryResolution(
                    item.repository_id, "duplicate_repository_root",
                    f"registry.resolution[{item.repository_id}].duplicate_repository_root",
                    None, item.declaration, item.binding, None,
                )
    return tuple(candidates)


def resolve_repository(
    registry: RepositoryRegistry, repository_id: str
) -> ResolvedRepository:
    """Fail closed unless one repository resolves to a validated Profile."""
    identifier = _identifier(repository_id, "registry.resolution.repository_id")
    for resolution in list_repository_resolutions(registry):
        if resolution.repository_id == identifier:
            if resolution.resolved_repository is not None:
                return resolution.resolved_repository
            raise _error(resolution.reason_code, "repository resolution is not available")
    raise _error(
        f"registry.resolution[{identifier}].repository_unknown",
        "repository is not declared",
    )


def repository_registry_to_mapping(registry: RepositoryRegistry) -> dict[str, Any]:
    if not isinstance(registry, RepositoryRegistry):
        raise TypeError("registry must be a RepositoryRegistry")
    validated = validate_repository_registry(registry)
    return {
        "registry": _registry_mapping(validated),
        "bindings": _bindings_mapping(validated.bindings),
    }


def serialize_repository_registry(registry: RepositoryRegistry) -> str:
    return json.dumps(
        repository_registry_to_mapping(registry),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


__all__ = [
    "DEFAULT_REPOSITORY_BINDINGS_PATH",
    "REPOSITORY_BINDINGS_SCHEMA_VERSION",
    "REPOSITORY_REGISTRY_SCHEMA_VERSION",
    "REPOSITORY_RESOLUTION_STATUSES",
    "RepositoryBinding",
    "RepositoryDeclaration",
    "RepositoryRegistry",
    "RepositoryRegistryValidationError",
    "RepositoryResolution",
    "ResolvedRepository",
    "list_repository_resolutions",
    "load_repository_bindings",
    "load_repository_registry",
    "repository_registry_to_mapping",
    "resolve_repository",
    "serialize_repository_registry",
    "validate_repository_bindings",
    "validate_repository_registry",
]
