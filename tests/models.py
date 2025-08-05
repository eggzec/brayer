"""Models shared across the test modules."""

from __future__ import annotations

import datetime
import decimal
import enum
import pathlib
import typing
import uuid

import annotated_types as at
import pydantic
from pydantic import BaseModel, Field


class Colour(str, enum.Enum):
    """A string-valued enum, the easy case."""

    red = "Red"
    green = "Green"


class Priority(enum.IntEnum):
    """An int-valued enum. Rendered blank by earlier versions."""

    low = 1
    high = 2


class Shade(enum.Enum):
    """An auto()-valued enum, so the values are bare ints."""

    dark = enum.auto()
    light = enum.auto()


class Address(BaseModel):
    """A nested model."""

    street: str = "Main St"
    postcode: str = "0000"


class Node(BaseModel):
    """A self-referential model, to prove recursion is bounded."""

    label: str = "root"
    child: Node | None = None


class Primitives(BaseModel):
    """One field per primitive handler."""

    text: str = "hello"
    count: int = 7
    ratio: float = 1.5
    flag: bool = True
    blob: bytes = b"bytes"
    when: datetime.datetime = datetime.datetime(2020, 1, 2, 3, 4)
    day: datetime.date = datetime.date(2020, 1, 2)
    clock: datetime.time = datetime.time(3, 4)
    span: datetime.timedelta = datetime.timedelta(seconds=90)
    ident: uuid.UUID = uuid.UUID(int=1)
    where: pathlib.Path = pathlib.Path("a/b")
    money: decimal.Decimal = decimal.Decimal("2.50")


class Constrained(BaseModel):
    """Fields carrying constraints that must reach the widgets."""

    age: int = Field(default=30, ge=0, le=150)
    exclusive: int = Field(default=5, gt=0, lt=10)
    name: str = Field(default="ab", max_length=8)
    money: decimal.Decimal = Field(
        default=decimal.Decimal("1.25"), decimal_places=2
    )


class Collections(BaseModel):
    """Every container shape the dispatcher supports."""

    tags: list[str] = Field(default_factory=list)
    positives: list[typing.Annotated[int, at.Gt(0)]] = Field(
        default_factory=list
    )
    unique: set[str] = Field(default_factory=set)
    frozen: frozenset[int] = Field(default_factory=frozenset)
    pair: tuple[int, str] = (1, "a")
    many: tuple[int, ...] = ()
    mapping: dict[str, int] = Field(default_factory=dict)


class SpecialForms(BaseModel):
    """Unions and literals."""

    nickname: str | None = None
    # typing.Union rather than `|`, so the dispatcher is exercised
    # against both spellings of a union.
    mixed: typing.Union[str, int]
    mode: typing.Literal["a", "b"] = "b"
    ambiguous: typing.Literal[1, "1"] = 1


class Aliased(BaseModel):
    """A model that can only be built from its aliases."""

    given_name: str = Field(default="Ada", alias="givenName")


class Person(BaseModel):
    """The model used in the documentation examples."""

    name: str
    age: int = Field(ge=0)
    birthday: datetime.date
    colour: Colour = Colour.red
    address: Address = Address()


class Unsupported(BaseModel):
    """Carries a type no handler claims."""

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    thing: object
