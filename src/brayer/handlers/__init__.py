"""Widget handlers, grouped by the kind of annotation they serve.

Importing this package registers every built-in handler as a side
effect. Handlers are registered rather than listed in a central
``if``/``elif`` chain, which is what lets a user add support for their
own types without editing this package -- see
:func:`brayer.register_handler`.

The modules are imported for their registrations only; nothing here
needs to be referenced directly.
"""

from __future__ import annotations

from . import pydantic_types, special_forms, std_types


__all__ = ["pydantic_types", "special_forms", "std_types"]
