from collections import Counter

from control_plane.app.services.config_service import BaseAppConfig


def _get_directly_declared_fields(cls):
    annotations = cls.__dict__.get("__annotations__", {})
    return {name for name in annotations if name in cls.model_fields}


def _get_field_aliases(cls):
    aliases = {}
    for name, field in cls.model_fields.items():
        alias = field.alias or name.upper()
        aliases.setdefault(alias, []).append(name)
    return aliases


def test_no_duplicate_field_names():
    field_names = list(BaseAppConfig.model_fields.keys())
    duplicates = {name for name, count in Counter(field_names).items() if count > 1}
    assert not duplicates, f"Duplicate field names found: {duplicates}"


def test_no_duplicate_field_aliases():
    aliases = _get_field_aliases(BaseAppConfig)
    duplicates = {alias: fields for alias, fields in aliases.items() if len(fields) > 1}
    assert not duplicates, f"Duplicate field aliases found: {duplicates}"


def test_no_duplicate_field_across_parents():
    declared = {}
    for klass in BaseAppConfig.__mro__:
        if not hasattr(klass, "model_fields"):
            continue
        for name in _get_directly_declared_fields(klass):
            if name in declared:
                raise AssertionError(
                    f"Field '{name}' is defined in both {declared[name].__name__} "
                    f"and {klass.__name__}. Each field must be defined in exactly "
                    "one parent class."
                )
            declared[name] = klass
