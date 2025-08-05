"""Exceptions raised by this package.

Every exception derives from :class:`InputError`, so callers can catch the
whole family with a single ``except`` clause.
"""

from __future__ import annotations


__all__ = [
    "InputError",
    "UnresolvedAnnotationError",
    "UnsupportedTypeError",
    "WidgetBuildError",
]


class InputError(Exception):
    """Base class for every error raised by this package."""


class UnsupportedTypeError(InputError, NotImplementedError):
    """No handler is registered for a field's type.

    Derives from :class:`NotImplementedError` as well, so code written
    against earlier releases keeps working.
    """

    def __init__(self, field_type: object) -> None:
        self.field_type = field_type
        super().__init__(
            f"No widget handler is registered for type `{field_type!r}`. "
            "Register one with `register_handler`, or open an issue if it "
            "should be supported out of the box."
        )


class UnresolvedAnnotationError(InputError):
    """A model carries a forward reference that could not be resolved.

    Usually means the model was defined inside a function body, or refers
    to a name that is not importable at the point the form is built.
    """

    def __init__(self, model: type, detail: str = "") -> None:
        self.model = model
        name = getattr(model, "__name__", repr(model))
        suffix = f" ({detail})" if detail else ""
        super().__init__(
            f"Model `{name}` has unresolved forward references{suffix}. "
            f"Call `{name}.model_rebuild()` once the referenced names are "
            "importable, then build the form again."
        )


class WidgetBuildError(InputError):
    """A handler failed while building a widget or reading its value.

    Qt swallows exceptions raised inside slots, so failures that would
    otherwise vanish into stderr are re-raised wrapped in this type.
    """

    def __init__(
        self, field_name: str, cause: BaseException | None = None
    ) -> None:
        self.field_name = field_name
        self.cause = cause
        detail = f": {cause}" if cause is not None else ""
        super().__init__(f"Field `{field_name}` could not be read{detail}")


def field_label(field: object, fallback: str = "<field>") -> str:
    """Return the most human-readable name available for a field.

    Args:
        field: A pydantic ``FieldInfo``, or anything with a ``title``.
        fallback: Returned when nothing better is available.

    Returns:
        The field's title if it has one, otherwise the fallback.
    """
    title = getattr(field, "title", None)
    return title if isinstance(title, str) and title else fallback
