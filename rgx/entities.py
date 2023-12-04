from __future__ import annotations
from typing import (
    Callable,
    NoReturn,
    Optional,
    Tuple,
    List,
    Union,
    cast,
    overload,
    Sequence,
    TYPE_CHECKING,
)

from wordstreamer import Context, Renderable as BaseRenderable, Renderer, TokenStream
from wordstreamer.internal_types import Comparator, Payload

if TYPE_CHECKING:
    from typing import Literal as LiteralType, Self


import re

CharType = Union[str, "CharRange", "Literal"]
LiteralPart = Union[Tuple["AnyRegexPattern", ...], List[CharType], str]
AnyRegexPattern = Union[LiteralPart, "RegexPattern"]
Processor = Callable[["RegexPattern"], "RegexPattern"]

OrResult = Union["Option", "Chars", "ReversedChars"]

priority_step = 1000


@overload
def pattern(literal: str, escape: LiteralType[False]) -> UnescapedLiteral:
    ...


@overload
def pattern(literal: str, escape: bool = True) -> Literal | Chars:
    ...


@overload
def pattern(
    literal: tuple[AnyRegexPattern, ...], escape: bool = True
) -> RegexPattern | NonCapturingGroup:
    ...


@overload
def pattern(literal: list[CharType], escape: bool = True) -> Chars:
    ...


@overload
def pattern(literal: AnyRegexPattern, escape: bool = True) -> RegexPattern:
    ...


def pattern(literal: AnyRegexPattern, escape: bool = True) -> RegexPattern:
    """

    A universal pattern constructor.

    - With a string, returns a literan pattern. with `escape=False` returns an unescaped pattern.
    - With a tuple, returns a non-capturing group of patterns (or just one pattern if tuple has one element)
    - With a list, returns a character group (`[...]`). List must consist of strings and CharRange

    """
    if isinstance(literal, RegexPattern):
        return literal

    if isinstance(literal, str):
        if not escape:
            return UnescapedLiteral(literal)
        if len(literal) == 1:
            return Chars([literal])
        return Literal(literal)

    if isinstance(literal, tuple):
        if len(literal) == 1:
            return pattern(literal[0])
        return NonCapturingGroup(Concat(*literal))

    if isinstance(literal, list):
        return Chars(literal)


def respect_priority(contents: AnyRegexPattern, other_priority: int) -> RegexPattern:
    return cast(
        RegexPattern,
        pattern(contents).respect_priority(
            _PriorityShell(other_priority),
        ),
    )


class RegexPattern(BaseRenderable):
    priority: int = 100 * priority_step
    optimized = False
    default_context: Context = Context(Renderer())

    def wrap(self):
        return NonCapturingGroup(self)

    def render(self, context: Context) -> TokenStream:
        """
        Internal method

        Returns a generator, that can be joined to get a pattern string representation
        """
        return NotImplemented

    def stream(self, context: Context) -> TokenStream:
        return self.render(context)

    def case_insensitive(self) -> RegexPattern:
        return self.set_flags("i")

    def merge_flags(self) -> RegexPattern:
        return self

    def optimize(self) -> RegexPattern:
        self = self.apply(lambda x: x.optimize())
        self = self.merge_flags()

        self.optimized = True
        return self

    def apply(self, fn: Processor) -> Self:
        return self

    @staticmethod
    def merge_flags_abstract(
        parts: Sequence[RegexPattern],
    ) -> tuple[Sequence[RegexPattern], set[str]]:
        common_flags: set[str] | None = None

        for part in parts:
            if not isinstance(part, FlagLike):
                return parts, set()

            flags = set(part.flags)

            if common_flags is None:
                common_flags = flags
            else:
                common_flags &= flags

        if not common_flags:
            return parts, set()

        new_parts: list[RegexPattern] = []

        for alt in parts:
            assert isinstance(alt, FlagLike)
            new_flags = "".join(f for f in alt.flags if f not in common_flags)

            if not new_flags:
                new_parts.append(alt.inner)
            elif new_flags != alt.flags:
                new_parts.append(LocalFlags(alt.inner, new_flags))
            else:
                new_parts.append(alt)

        return new_parts, common_flags

    def render_str(self, flags: str = "", payload: Payload | None = None) -> str:
        """

        Renders given pattern into a string with specified global flags.

        """

        renderer = Renderer(payload)

        parts: list[BaseRenderable] = []

        if flags:
            parts.append(GlobalFlags(flags))

        parts.append(self.optimize())

        return "".join(map(renderer.render_string, parts))

    def __repr__(self) -> str:
        return self.render_str()

    def set_flags(self, flags: str) -> LocalFlags:
        """
        This method adds local flags to given pattern

        ```python
        x.flags("y") # "(?y:x)"
        ```
        """
        return LocalFlags(self, flags)

    def __add__(self, other: AnyRegexPattern) -> Concat:
        return Concat(self, other)

    def __radd__(self, other: AnyRegexPattern) -> Concat:
        return Concat(other, self)

    def concat(self, other: AnyRegexPattern) -> Concat:
        """
        Use to match one pattern and then another.

        `A.concat(B)` is equivalent to `A + B` (if either A or B is a RegexPart object, not a Python literal)

        ```python
        x.concat(y) # "xy"
        x + y # "xy"
        ```
        """
        return self + other

    def __or__(self, other: AnyRegexPattern) -> OrResult:
        return Option(self, other)

    def __ror__(self, other: AnyRegexPattern) -> OrResult:
        return respect_priority(other, Option.priority) | self

    def option(self, other: AnyRegexPattern) -> OrResult:
        """
        Use to match either one pattern or another.

        `A.option(B)` is equivalent to `A | B` (if either A or B is a RegexPart object, not a Python literal)

        ```python
        x.option(y) # "x|y"
        x | y # "x|y"
        ```
        """
        return self | other

    def repeat(self, count: int, lazy: bool = False) -> Range:
        return Range(self, min_count=count, max_count=count, lazy=lazy)

    def __mul__(self, other: int) -> Range:
        return self.repeat(other)

    repeat_from = repeat

    def many(self, lazy: bool = False) -> Range:
        """
        Use this for repeating patterns (one or more times)

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        ```python
        x.many() # "x+"
        x.many(True) # "x+?"
        ```
        """
        result: Range = self.repeat(1, lazy).or_more()
        return result

    def plus(self, lazy: bool = False):
        """alias for .many"""
        return self.many(lazy)

    def __pos__(self):
        return self.many()

    def some(self, lazy: bool = False) -> Range:
        """
        Use this for repeating optional patterns (zero or more times)

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        ```python
        x.some() # "x*"
        x.some(True) # "x*?"
        ```
        """

        return self.repeat(0, lazy).or_more()

    def star(self, lazy: bool = False):
        """alias for .some"""
        return self.some(lazy)

    def maybe(self, lazy: bool = False) -> Range:
        """
        Use this for optional patterns (zero or one times)

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        ```python
        x.maybe() # "x?"
        x.maybe(True) # "x??"
        ```
        """
        return self.repeat(1, lazy).or_less()

    def optional(self, lazy: bool = False):
        """alias for .maybe"""
        return self.maybe(lazy)

    def x_or_less_times(self, count: int, lazy: bool = False) -> Range:
        """

        Use this to match pattern x or less times (hence the name).

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        ```python
        x.x_or_less_times(5) # "x{,5}"
        x.x_or_less_times(5, True) # "x{,5}?"
        ```
        """
        return self.repeat(count, lazy).or_less()

    def x_or_more_times(self, count: int, lazy: bool = False) -> Range:
        """

        Use this to match pattern x or more times (hence the name).

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        ```python
        x.x_or_more_times(5) # "x{5,}"
        x.x_or_more_times(5, True) # "x{5,}?"
        ```
        """
        return self.repeat(count, lazy).or_more()

    def x_times(self, count: int, lazy: bool = False) -> Range:
        """

        Use this to match pattern exactly x times (hence the name).

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        ```python
        x.x_times(5) # "x{5}"
        x.x_times(5, True) # "x{5}?"
        ```
        """
        return self.repeat(count, lazy)

    def between_x_y_times(
        self, min_count: int, max_count: int, lazy: bool = False
    ) -> Range:
        """

        Use this to match pattern between x and y times, inclusive (hence the name).

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        ```python
        x.between_x_y_times(5, 6) # "x{5,6}"
        x.between_x_y_times(5, 6, True) # "x{5,6}?"
        ```
        """
        return self.repeat(min_count, lazy).to(max_count)

    def lookahead(self, other: AnyRegexPattern) -> Concat:
        """
        Use this to indicate that given pattern occurs before some another pattern (lookahead).

        In other words, `x.lookahead(y)` matches a pattern `x` only if there is `y` after it

        Lookahead pattern won't be captured.

        ```python
        x.lookahead(y) # x(?=y)
        x.before(y) # x(?=y)
        ```
        """
        return Concat(self, Lookahead(other))

    def before(self, other: AnyRegexPattern) -> Concat:
        """alias for .lookahead"""
        return self.lookahead(other)

    def negative_lookahead(self, other: AnyRegexPattern) -> Concat:
        """
        Use this to indicate that given pattern doesn't occur before some another pattern (negative lookahead).

        In other words, `x.negative_lookahead(y)` matches a pattern `x` only if there is no `y` after it

        Lookahead pattern won't be captured.

        ```python
        x.negative_lookahead(y) # x(?!y)
        x.not_before(y) # x(?!y)
        ```
        """
        return Concat(self, NegativeLookahead(other))

    def not_before(self, other: AnyRegexPattern) -> Concat:
        """alias for .negative_lookahead"""
        return self.negative_lookahead(other)

    def lookbehind(self, other: AnyRegexPattern) -> Concat:
        """
        Use this to indicate that given pattern occurs after some another pattern (lookbehind).

        In other words, `x.lookbehind(y)` matches a pattern `x` only if there is `y` before it

        Lookbehind pattern won't be captured.

        ```python
        x.lookbehind(y) # (?<=y)x
        x.after(y) # (?<=y)x
        ```
        """
        return Concat(Lookbehind(other), self)

    def after(self, other: AnyRegexPattern) -> Concat:
        """alias for .lookbehind"""
        return self.lookbehind(other)

    def negative_lookbehind(self, other: AnyRegexPattern) -> Concat:
        """
        Use this to indicate that given pattern goes before some another pattern (negative lookbehind).

        In other words, `x.negative_lookbehind(y)` matches a pattern `x` only if there is NO `y` before it

        Lookbehind pattern won't be captured.

        ```python
        x.negative_lookbehind(y) # (?<!y)x
        x.not_after(y) # (?<!y)x
        ```
        """
        return Concat(NegativeLookbehind(other), self)

    def not_after(self, other: AnyRegexPattern) -> Concat:
        """alias for .negative_lookbehind"""
        return self.negative_lookbehind(other)

    def comment(self, text: str) -> Concat:
        """leaves a comment in expression (if needed for whatever reason)"""
        return Concat(self, Comment(UnescapedLiteral(text.replace(")", "\\)"))))

    def capture(self) -> Group:
        """

        Use this to make a capturing group out of pattern.

        ```python
        x.capture() # (x)
        ```
        """
        return Group(self)

    def named(self, name: str) -> NamedPattern:
        return NamedPattern(name, self)


class _PriorityShell(RegexPattern):
    def __init__(self, priority: int) -> None:
        self.priority = priority


class GroupBase(RegexPattern):
    contents: RegexPattern
    prefix: str

    def __init__(self, *contents: AnyRegexPattern):
        self.contents = pattern(contents)

    def render_prefix(self) -> TokenStream:
        yield self.prefix

    def case_insensitive(self):
        return self.apply(lambda x: x.case_insensitive())

    def render(self, context: Context) -> TokenStream:
        yield "("
        yield from self.render_prefix()
        yield from self.contents.render(context)
        yield ")"

    def apply(self, fn: Processor) -> Self:
        return self.__class__(fn(self.contents))


class Group(GroupBase):
    prefix = ""


class NonCapturingGroup(GroupBase):
    prefix = "?:"

    def optimize(self) -> RegexPattern:
        if isinstance(self.contents, NonCapturingGroup):
            return self.contents.optimize()
        return super().optimize()

    def respect_priority(
        self,
        operation: BaseRenderable,
        comparator: Comparator | None = None,
        side: str = "none",
    ) -> BaseRenderable:
        return self.contents.respect_priority(operation, comparator, side)


class Lookahead(GroupBase):
    prefix = "?="


class NegativeLookahead(GroupBase):
    prefix = "?!"


class Lookbehind(GroupBase):
    prefix = "?<="


class NegativeLookbehind(GroupBase):
    prefix = "?<!"


class Comment(GroupBase):
    prefix = "?#"


def sort_chartype(seq: Sequence[CharRange]) -> Sequence[CharRange]:
    def sorting_func(char: CharRange) -> tuple[int, int]:
        return char.start, char.stop

    return sorted(seq, key=sorting_func)


def make_range(part: CharType) -> CharRange:
    if isinstance(part, str):
        return CharRange(part, part)
    if isinstance(part, Literal):
        return CharRange(part.contents, part.contents)
    return part


def merge_chars(contents: Sequence[CharType]) -> Sequence[CharRange]:
    result: list[CharRange] = []
    contents = sort_chartype([make_range(part) for part in contents])

    def merge_parts(last_part: CharRange, next_part: CharRange) -> Sequence[CharRange]:
        if last_part.stop + 1 >= next_part.start:
            if next_part.stop > last_part.stop:
                return [CharRange(last_part.start, next_part.stop)]
            return [last_part]

        return [last_part, next_part]

    for part in contents:
        if len(result):
            result[-1:] = merge_parts(result[-1], part)
        else:
            result.append(part)

    return result


Bounds = Tuple[int, int]


class FlagLike(RegexPattern):
    flags: str
    inner: RegexPattern


class CharBase(FlagLike):
    def __init__(self, contents: Sequence[CharType]):
        self.contents = list(merge_chars(contents))
        self.inner = self

    @property
    def flags(self):
        ci = self.case_insensitive()
        if ci == self:
            return "i"
        return ""

    def __eq__(self, other: object):
        if not isinstance(other, self.__class__):
            return False

        if len(self.contents) != len(other.contents):
            return False

        for i, r in enumerate(self.contents):
            if r != other.contents[i]:
                return False

        return True

    def case_insensitive(self) -> Self:
        contents: list[CharRange] = []

        for part in self.contents:
            start_char = chr(part.start)
            stop_char = chr(part.stop)

            is_lower = start_char.islower() and stop_char.islower()
            is_upper = start_char.isupper() and stop_char.isupper()

            if is_lower:
                upper_chars = map(ord, map(str.upper, (start_char, stop_char)))
                contents.append(CharRange(*upper_chars))

            elif is_upper:
                lower_chars = map(ord, map(str.lower, (start_char, stop_char)))
                contents.append(CharRange(*lower_chars))

            contents.append(part)

        return self.__class__(contents)


class Chars(CharBase):
    non_special = {".", "[", "|", "~", "*", "(", ")", "+", "$", "&", "?", "#"}

    def accepts(self, char: str) -> bool:
        for chrange in self.contents:
            if chrange.accepts(char):
                return True
        return False

    def render(self, context: Context) -> TokenStream:
        if len(self.contents) == 1:
            contents = self.contents[0]
            if contents.is_single_char():
                yield from contents.render_literal(context)
                return
        yield "["

        for char in self.contents:
            yield from char.render(context)

        yield "]"

    def to(self, other: str | Literal | Chars) -> Chars:
        if isinstance(other, str):
            end = pattern(other)
        elif isinstance(other, Chars):
            end = other
        else:
            end = other

        start: int = self.contents[0].start

        stop_base = end.contents[0]
        stop: int
        if isinstance(stop_base, str):
            stop = ord(stop_base)
        else:
            stop = stop_base.stop

        return char_range(start, stop)

    def reverse(self) -> ReversedChars:
        return ReversedChars(self.contents)

    @overload
    def __or__(self, other: Chars | list[CharType]) -> Chars:
        ...

    @overload
    def __or__(self, other: AnyRegexPattern) -> Option | Chars:
        ...

    def __or__(self, other: AnyRegexPattern) -> Union[Option, Chars]:
        other = respect_priority(other, Option.priority)
        if isinstance(other, Chars):
            return Chars([*self.contents, *other.contents])
        return Option(self, other)

    def exclude(self, chars: AnyRegexPattern) -> Chars:
        chars = pattern(chars)
        if not isinstance(chars, Chars):
            raise ValueError(
                "Can't exclude non-Chars pattern, don't really know how..."
            )
        result = []
        for part in self.contents:
            result.extend(part.exclude(chars))
        return Chars(result)


class ReversedChars(CharBase):
    def render(self, context: Context) -> TokenStream:
        yield "["
        yield "^"
        for char in self.contents:
            if isinstance(char, (Literal, CharRange)):
                yield from char.render(context)
            elif char in Chars.non_special:
                yield char
            else:
                yield re.escape(char)
        yield "]"

    def reverse(self) -> Chars:
        return Chars(self.contents)

    @overload
    def __or__(self, other: ReversedChars) -> ReversedChars:
        ...

    @overload
    def __or__(self, other: AnyRegexPattern) -> Option | ReversedChars:
        ...

    def __or__(self, other: AnyRegexPattern) -> Union[Option, ReversedChars]:
        other = respect_priority(other, Option.priority)
        if isinstance(other, ReversedChars):
            return ReversedChars([*self.contents, *other.contents])
        return Option(self, other)


class CharRange(BaseRenderable):
    min_char = 0
    max_char = 0x10FFFF

    def __init__(self, start: Optional[str | int], stop: Optional[str | int]):
        meta = None
        if isinstance(start, str):
            if len(start) > 1:
                meta = start
                start = -1
            else:
                start = ord(start)
        if isinstance(stop, str):
            if len(stop) > 1:
                stop = -1
            else:
                stop = ord(stop)

        self.start = start or CharRange.min_char
        self.stop = stop or CharRange.max_char
        self.meta = meta

        if not (start or stop):
            raise ValueError(
                "Cannot create a character range with no data. Use rgx.meta.ANY instead"
            )

    def accepts(self, char: str) -> bool:
        return ord(char) in range(self.start, self.stop + 1)

    @staticmethod
    def render_char(char: int) -> str:
        return re.escape(chr(char))

    def stream(self, context: Context) -> TokenStream:
        if self.meta:
            yield self.meta
            return

        diff = self.stop - self.start

        if self.start:
            yield self.render_char(self.start)

        if not diff:
            return  # one char

        if diff == 2:
            yield chr(self.stop - 1)  # render 012 instead of 0-2

        if diff > 2:
            yield "-"

        if self.stop != CharRange.max_char:
            yield self.render_char(self.stop)

    def render(self, context: Context) -> TokenStream:
        return self.stream(context)

    def render_literal(self, context: Context) -> TokenStream:
        if self.meta:
            yield self.meta
            return
        yield from Literal(chr(self.start)).render(context)

    @staticmethod
    def exclude_bounds(bounds: Bounds, exclude: Bounds) -> list[Bounds]:
        result: list[Bounds] = []
        self_range = range(bounds[0], bounds[1] + 1)

        if exclude[0] - 1 in self_range:
            result.append((bounds[0], exclude[0] - 1))
        if exclude[1] + 1 in self_range:
            result.append((exclude[1] + 1, bounds[1]))
        return result

    def exclude(self, chars: Chars) -> list[CharRange]:
        if self.meta:
            raise ValueError(
                f"Cannot exclude chars '{chars}' from meta-sequence '{self.meta}'"
            )

        result: list[Bounds] = [(self.start, self.stop)]
        temp_result: list[Bounds] = []
        cut_start = 0
        last_cut_start = 0

        for char_part in chars.contents:
            if char_part.meta:
                raise ValueError(
                    f"Cannot exclude meta-sequence '{self.meta}' from chars '[{self}]'"
                )
            exclude = (char_part.start, char_part.stop)
            for i, bounds in enumerate(result[cut_start:], start=cut_start):
                if exclude[1] < bounds[0]:
                    temp_result.extend(result[i:])
                    break

                if exclude[0] > bounds[1]:
                    temp_result.append(result[i])
                    continue

                temp_result.extend(self.exclude_bounds(bounds, exclude))

            last_cut_start = cut_start
            cut_start = len(temp_result) - 1

            result[last_cut_start:] = temp_result
            temp_result = []

        return [CharRange(*x) for x in result]

    def is_single_char(self) -> bool:
        return self.start == self.stop

    def __repr__(self):
        return Renderer().render_string(self)

    def __eq__(self, other: object):
        if not isinstance(other, CharRange):
            return False

        return (
            self.start == other.start
            and self.stop == other.stop
            and self.meta == other.meta
        )


@overload
def char_range(start: Optional[str | int], stop: str | int) -> Chars:
    ...


@overload
def char_range(start: str | int, stop: None = None) -> Chars:
    ...


@overload
def char_range(start: None = None, stop: None = None) -> NoReturn:
    ...


@overload
def char_range(start: Optional[str | int], stop: Optional[str | int]) -> Chars:
    ...


def char_range(
    start: Optional[str | int] = None, stop: Optional[str | int] = None
) -> Chars:
    """

    Use this for character ranges (e.g. `[a-z]`)

    Can be combined with other Chars istances (or lists) using |

    `start` and `stop` are inclusive

    """

    return Chars([CharRange(start, stop)])


class Concat(RegexPattern):
    priority = 2 * priority_step

    def __init__(self, *contents: AnyRegexPattern) -> None:
        if len(contents) >= 3:
            contents = (contents[0], Concat(*contents[1:]))

        self.contents = [respect_priority(part, self.priority) for part in contents]

    def __add__(self, other: AnyRegexPattern) -> Concat:
        return Concat(*self.contents, other)

    def case_insensitive(self) -> RegexPattern:
        return self.apply(lambda x: x.case_insensitive())

    def render(self, context: Context) -> TokenStream:
        for part in self.contents:
            yield from part.render(context)

    def merge_flags(self) -> LocalFlags | Concat:
        processed, common_flags = self.merge_flags_abstract(self.contents)

        new = Concat(*processed)

        if not common_flags:
            return new

        return LocalFlags(new, "".join(common_flags))

    def apply(self, fn: Processor) -> Self:
        return self.__class__(*map(fn, self.contents))


class Option(RegexPattern):
    priority = 0 * priority_step

    def __init__(self, *alternatives: AnyRegexPattern):
        if len(alternatives) >= 3:
            alternatives = (alternatives[0], Option(*alternatives[1:]))

        self.alternatives = [
            respect_priority(alternative, self.priority) for alternative in alternatives
        ]

    def case_insensitive(self) -> RegexPattern:
        return self.apply(lambda x: x.case_insensitive())

    def merge_flags(self) -> LocalFlags | Option:
        processed, common_flags = self.merge_flags_abstract(self.alternatives)

        new = Option(*processed)

        if not common_flags:
            return new

        return LocalFlags(new, "".join(common_flags))

    def render(self, context: Context) -> TokenStream:
        if not self.alternatives:
            return
        yield from self.alternatives[0].render(context)
        for alternative in self.alternatives[1:]:
            yield "|"
            yield from alternative.render(context)

    def __or__(self, other: AnyRegexPattern) -> Option:
        return Option(*self.alternatives, other)

    def __ror__(self, other: AnyRegexPattern) -> Option:
        return Option(other, *self.alternatives)

    def apply(self, fn: Processor) -> Self:
        return self.__class__(*map(fn, self.alternatives))


class LocalFlags(FlagLike):
    def __init__(self, contents: AnyRegexPattern, flags: str):
        self.contents = pattern(contents)
        self.inner = self.contents
        self.flags = flags

    def case_insensitive(self) -> RegexPattern:
        return self.apply(lambda x: x.case_insensitive())

    def render(self, context: Context) -> TokenStream:
        yield "(?"
        yield self.flags
        yield ":"
        yield from self.contents.render(context)
        yield ")"

    def apply(self, fn: Processor) -> Self:
        return self.__class__(fn(self.contents), self.flags)


class GlobalFlags(GroupBase):
    prefix = "?"

    def __init__(self, contents: str):
        self.contents = Literal(contents)


class Range(RegexPattern):
    priority: int = 3 * priority_step

    def __init__(
        self,
        *contents: AnyRegexPattern,
        min_count: int = 0,
        max_count: Optional[int] = None,
        lazy: bool = False,
    ) -> None:
        if min_count == max_count == 1:
            self.contents = pattern(contents)
        else:
            self.contents = respect_priority(contents, self.priority + 1)

        if max_count is not None and min_count > max_count:
            min_count, max_count = max_count, min_count

        if min_count < 0:
            raise ValueError("Quantifier lower bound cannot be less than 0")

        if max_count is not None and max_count < 0:
            raise ValueError("Quantifier upper bound cannot be less than 0")

        self.min_count = min_count
        self.max_count = max_count
        self.lazy = lazy

    def case_insensitive(self) -> RegexPattern:
        return self.apply(lambda x: x.case_insensitive())

    def repeat(self, count: int, lazy: bool = False) -> Range:
        """

        The logic here should be carefully thought through.
        If we multiply a fixed-size pattern a{X} by Y, we generally DO NOT get a{X*Y}
        If we multiply a .or_less() pattern a{,X} by Y, we get a{,X*Y}
        If we multiply a pattern a{1,X} (X!=1) by Y, we get a{Y,X*Y}

        Above logic doesn't scale up with patterns a{X,N} * Y, if X is not in {0, 1}, so we should fallback to (?:a{X,N}){Y}

        While it is easy to say a{X} * Y == a{X*Y} (i.e. a{5} * 10 == a{50}),
        ...this doesn't work well with .many() and other quantifiers: (a{5} * 10).many() != a{50,}
        ...but rather (?:a{5}){10,}

        """

        if self.min_count not in {0, 1}:
            return super().repeat(count, lazy)

        max_count = self.max_count * count if self.max_count else None
        return Range(
            self.contents,
            min_count=self.min_count * count,
            max_count=max_count,
            lazy=lazy,
        )

    def or_more(self) -> Range:
        return Range(self.contents, min_count=self.min_count, lazy=self.lazy)

    def __pos__(self) -> Range:
        return self.or_more()

    def or_less(self) -> Range:
        return Range(
            self.contents, min_count=0, max_count=self.max_count, lazy=self.lazy
        )

    def __neg__(self) -> Range:
        return self.or_less()

    def to(self, count: int) -> Range:
        return Range(
            self.contents, min_count=self.min_count, max_count=count, lazy=self.lazy
        )

    def __rshift__(self, count: int) -> Range:
        return self.to(count)

    def render_quantifier(self) -> TokenStream:
        if self.max_count is None:
            if not self.min_count:
                yield "*"
                return
            elif self.min_count == 1:
                yield "+"
                return

        elif self.max_count == 1:
            if not self.min_count:
                yield "?"
                return
            elif self.min_count == 1:
                return

        yield "{"

        if self.min_count:
            yield str(self.min_count)

        if self.min_count == self.max_count:
            yield "}"
            return

        yield ","

        if self.max_count:
            yield str(self.max_count)

        yield "}"

    def render(self, context: Context) -> TokenStream:
        if self.max_count == 0:
            return

        yield from self.contents.render(context)

        if self.min_count == self.max_count == 1:
            return

        yield from self.render_quantifier()

        if self.lazy and self.min_count != self.max_count:
            yield "?"

    def merge_flags(self) -> LocalFlags | Range:
        processed, common_flags = self.merge_flags_abstract([self.contents])

        if not common_flags:
            return self

        return LocalFlags(
            self.apply(lambda _: processed[0]),
            "".join(common_flags),
        )

    def apply(self, fn: Processor) -> Self:
        return self.__class__(
            fn(self.contents),
            min_count=self.min_count,
            max_count=self.max_count,
            lazy=self.lazy,
        )


class NamedPattern(RegexPattern):
    """

    Named capturing group.

    If `contents` are omitted, generates a reference, otherwise a named group definition.

    ```python
    pattern.named("x", y) # (?P<x>y)
    pattern.named("x") # (?P=x)
    ```
    """

    def __init__(self, name: str, contents: Optional[AnyRegexPattern] = None):
        self.name = name
        self.contents = pattern(contents) if contents is not None else None

    def case_insensitive(self) -> RegexPattern:
        contents = self.contents.case_insensitive() if self.contents else None
        return NamedPattern(self.name, contents)

    def render(self, context: Context) -> TokenStream:
        yield "(?P"
        if self.contents:
            yield "<"
            yield self.name
            yield ">"
            yield from self.contents.render(context)
        else:
            yield "="
            yield self.name
        yield ")"

    def merge_flags(self) -> LocalFlags | NamedPattern:
        if self.contents is None:
            return self

        processed, common_flags = self.merge_flags_abstract([self.contents])

        if not common_flags:
            return self

        return LocalFlags(
            self.apply(lambda _: processed[0]),
            "".join(common_flags),
        )

    def apply(self, fn: Processor) -> Self:
        if self.contents is None:
            return self

        return self.__class__(
            self.name,
            fn(self.contents),
        )


class ConditionalPattern(RegexPattern):
    """
    Use to match different patterns depending on whether another group matched or not.

    Next two snippets produce effectively the same result:

    ```python
    from rgx import pattern

    hello = pattern("hello").capture()
    world = pattern("world")
    where = pattern("where")

    x = (hello + world) | where
    ```

    ```python
    from rgx import pattern, conditional

    hello = pattern("hello").capture()
    world = pattern("world")
    where = pattern("where")

    x = hello.maybe() + conditional(1, world, where)
    ```
    """

    def __init__(
        self, group: int, true_option: AnyRegexPattern, false_option: AnyRegexPattern
    ) -> None:
        self.group = group
        self.true_option = respect_priority(true_option, Option.priority + 1)
        self.false_option = respect_priority(false_option, Option.priority + 1)

    def render(self, context: Context) -> TokenStream:
        yield "(?("
        yield str(self.group)
        yield ")"
        yield from self.true_option.render(context)
        yield "|"
        yield from self.false_option.render(context)
        yield ")"

    def apply(self, fn: Processor) -> Self:
        return self.__class__(
            self.group,
            fn(self.true_option),
            fn(self.false_option),
        )

    def case_insensitive(self) -> RegexPattern:
        return self.apply(lambda x: x.case_insensitive())


class Literal(RegexPattern):
    def __init__(self, contents: str) -> None:
        self.contents: str = contents
        if len(self.contents) != 1:
            self.priority = 2 * priority_step

    def to(self, other: str | Literal | Chars) -> Chars:
        return Chars([self]).to(other)

    def render(self, context: Context) -> TokenStream:
        yield re.escape(self.contents)

    def apply(self, fn: Processor) -> Self:
        return self


class UnescapedLiteral(Literal):
    """

    Unescaped literal. Renders into whatever is passed (as long as it is a string)

    """

    def render(self, context: Context) -> TokenStream:
        yield str(self.contents)


def group_reference(group: int) -> UnescapedLiteral:
    """

    Renders into a group reference (backreference)
    E.g. if Group #1 is `(x|y)` and it has matched "x", `reference(1)` would match exactly "x", but not "y"

    ```python
    rgx.reference(1) # \\1
    ```

    """
    return UnescapedLiteral(f"\\{group}")
