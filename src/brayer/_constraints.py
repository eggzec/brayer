"""Read pydantic field constraints and map them onto Qt widget limits.

Pydantic stores ``Field(ge=..., max_length=...)`` as a list of metadata
objects on ``FieldInfo.metadata`` -- ``annotated_types.Ge``, ``MaxLen``,
and pydantic's own ``_PydanticGeneralMetadata`` for ``decimal_places``.
They share no common base class, but each exposes its constraint as a
plainly-named attribute, so they can be read uniformly with ``getattr``.
"""

from __future__ import annotations

import dataclasses
import decimal
import typing


__all__ = ["Constraints", "read_constraints"]

# Attribute names carried by annotated_types and pydantic metadata
# objects. Anything absent stays None.
_CONSTRAINT_FIELDS = (
    "ge",
    "gt",
    "le",
    "lt",
    "min_length",
    "max_length",
    "pattern",
    "multiple_of",
    "max_digits",
    "decimal_places",
)

# Qt spin boxes are backed by a C++ int, so the usable range is bounded
# by the 32-bit signed limits no matter what the annotation allows.
INT_MIN = -(2**31)
INT_MAX = 2**31 - 1

# QDoubleSpinBox is backed by a C++ double; these bounds keep the
# displayed range readable rather than scientific.
FLOAT_MIN = -1e12
FLOAT_MAX = 1e12

DEFAULT_DECIMALS = 4


@dataclasses.dataclass(frozen=True)
class Constraints:
    """The constraints declared on a single pydantic field."""

    ge: typing.Any = None
    gt: typing.Any = None
    le: typing.Any = None
    lt: typing.Any = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    multiple_of: typing.Any = None
    max_digits: int | None = None
    decimal_places: int | None = None

    def int_range(self) -> tuple[int, int]:
        """Return the inclusive integer range a spin box should allow.

        Exclusive bounds are converted to inclusive ones by stepping a
        single unit inward, which is exact for integers.

        Returns:
            A ``(minimum, maximum)`` pair clamped to Qt's 32-bit range.
        """
        low = INT_MIN
        if self.ge is not None:
            low = int(self.ge)
        elif self.gt is not None:
            low = int(self.gt) + 1

        high = INT_MAX
        if self.le is not None:
            high = int(self.le)
        elif self.lt is not None:
            high = int(self.lt) - 1

        low = max(INT_MIN, min(low, INT_MAX))
        high = max(INT_MIN, min(high, INT_MAX))
        return (low, high) if low <= high else (high, low)

    def float_range(self, step: float) -> tuple[float, float]:
        """Return the range a double spin box should allow.

        Args:
            step: The widget's single-step, used to step inward from an
                exclusive bound. A spin box cannot express "greater than"
                so the nearest representable value is used instead.

        Returns:
            A ``(minimum, maximum)`` pair.
        """
        low = FLOAT_MIN
        if self.ge is not None:
            low = float(self.ge)
        elif self.gt is not None:
            low = float(self.gt) + step

        high = FLOAT_MAX
        if self.le is not None:
            high = float(self.le)
        elif self.lt is not None:
            high = float(self.lt) - step

        return (low, high) if low <= high else (high, low)

    def decimals(self, default: int = DEFAULT_DECIMALS) -> int:
        """Return how many decimal places a numeric widget should show.

        Args:
            default: Used when the field declares no ``decimal_places``.

        Returns:
            A non-negative count of decimal places.
        """
        if self.decimal_places is not None:
            return max(0, int(self.decimal_places))
        return default

    def step(self) -> float:
        """Return a sensible single-step for a numeric widget.

        Returns:
            ``multiple_of`` when declared, otherwise a step matching the
            field's decimal precision.
        """
        if self.multiple_of is not None:
            return float(self.multiple_of)
        if self.decimal_places is not None:
            return float(decimal.Decimal(1).scaleb(-self.decimals()))
        return 1.0


def read_constraints(field: object) -> Constraints:
    """Extract every constraint pydantic recorded for a field.

    Args:
        field: A pydantic ``FieldInfo``, or any object exposing a
            ``metadata`` sequence. Objects without one yield empty
            constraints rather than raising.

    Returns:
        A :class:`Constraints` holding whatever was declared.
    """
    found: dict[str, typing.Any] = {}
    for meta in getattr(field, "metadata", ()) or ():
        for name in _CONSTRAINT_FIELDS:
            value = getattr(meta, name, None)
            if value is not None:
                found[name] = value
    return Constraints(**found)
