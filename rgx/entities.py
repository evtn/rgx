from __future__ import annotations
from typing import NoReturn, Optional, Union, overload, Iterable, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal as LiteralType

import itertools
import re

StrGen = Iterable[str]
CharType = Union[str, "CharRange", "Literal"]
LiteralPart = Union["tuple[AnyRegexPattern, ...]", "list[CharType]", str]
AnyRegexPattern = Union[LiteralPart, "RegexPattern"]

OrResult = Union["Option", "Chars", "ReversedChars"]

priority_step = 1000


@overload
def pattern(literal: str, escape: LiteralType[False]) -> UnescapedLiteral:
    ...
@overload
def pattern(literal: str, escape: bool = True) -> Literal | Chars:
    ...
@overload
def pattern(literal: tuple[AnyRegexPattern], escape: bool = True) -> Union[RegexPattern, NonCapturingGroup]:
    ...
@overload
def pattern(literal: list[CharType], escape: bool = True) -> Chars:
    ...
@overload
def pattern(literal: RegexPattern, escape: bool = True) -> RegexPattern:
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
    return literal


def respect_priority(contents_: AnyRegexPattern, other_priority: int) -> RegexPattern:
    contents: RegexPattern = (
        pattern(contents_)
    )
    if contents.priority < other_priority:
        return NonCapturingGroup(contents)
    return contents


class RegexPattern:
    priority: int = 100 * priority_step
    def render(self) -> StrGen:
        """
        Internal method

        Returns a generator, that can be joined to get a pattern string representation
        """
        return NotImplemented

    def render_str(self, flags: str = "") -> str:
        """
        
        Renders given pattern into a string with specified global flags.

        """
        contents: Iterable[str]
        if flags:
            contents = itertools.chain(GlobalFlags(flags).render(), self.render())
        else:
            contents = self.render()

        return "".join(contents)

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

    def between_x_y_times(self, min_count: int, max_count: int, lazy: bool = False) -> Range:
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
        """ leaves a comment in expression (if needed for whatever reason) """
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

class GroupBase(RegexPattern):
    contents: RegexPattern
    prefix: str

    def __init__(self, *contents: AnyRegexPattern):
        self.contents = pattern(contents)

    def render_prefix(self) -> StrGen:
        yield self.prefix

    def render(self) -> StrGen:
        yield "("
        yield from self.render_prefix()
        yield from self.contents.render()
        yield ")"


class Group(GroupBase):
    prefix = ""

class NonCapturingGroup(GroupBase):
    prefix = "?:"

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

def sort_chartype(seq: Sequence[CharType]) -> Sequence[CharType]:
    def sorting_func(char: CharType) -> tuple[int, int]:
        if isinstance(char, Literal):
            char_num = ord(char.contents)
            return (char_num, char_num)
        if isinstance(char, CharRange):
            return (ord(char.start or chr(0)), ord(char.stop or chr(0x10ffff)))
        return (ord(char), ord(char))

    return sorted(
        seq,
        key=sorting_func
    )

def merge_chars(contents: Sequence[CharType]) -> Sequence[CharRange]:
    result: list[CharRange] = []
    contents = sort_chartype(contents)

    def make_range(part: CharType) -> CharRange:
        if isinstance(part, str):
            return CharRange(part, part)
        if isinstance(part, Literal):
            return CharRange(part.contents, part.contents)
        return part

    def merge_parts(last_part: CharRange, next_part: CharType) -> Sequence[CharRange]:
        next_part = make_range(next_part)

        if ord(last_part.stop or chr(0)) + 1 >= ord(next_part.start or chr(0x10FFFF)):
            if next_part.stop is None or next_part.stop > (last_part.stop or chr(0)):
                return [CharRange(last_part.start, next_part.stop)]
            return [last_part]

        return [last_part, next_part]

    for part in contents:
        if len(result):
            merged = merge_parts(result[-1], part)
            if len(merged) == 1:
                result[-1] = merged[0]
            else:
                result.append(merged[1])
        else:
            result.append(make_range(part))

    return result


class Chars(RegexPattern):
    non_special = {".", "[", "|", "~", "*", "(", ")", "+", "$", "&", "?", "#"}
    def __init__(self, contents: Sequence[CharType], is_reversed: bool = False):
        self.contents = list(merge_chars(contents))

    def render(self) -> StrGen:
        if len(self.contents) == 1:
            contents = self.contents[0]
            if contents.start and contents.is_single_char():
                yield from Literal(contents.start).render()
                return
        yield "["
        for char in self.contents:
            if isinstance(char, (Literal, CharRange)):
                yield from char.render()
            elif char in Chars.non_special:
                yield char
            else:
                yield re.escape(char)
        yield "]"

    def to(self, other: str | Literal | Chars) -> Chars:
        if isinstance(other, str):
            end = pattern(other)
        elif isinstance(other, Chars):
            end = other
        else:
            end = other

        start_base = self.contents[0]
        start: str | None

        if isinstance(start_base, str):
            start = start_base
        elif isinstance(start_base, CharRange):
            start = start_base.start
        else:
            start = start_base.contents

        stop_base = end.contents[0]
        stop: str | None
        if isinstance(stop_base, str):
            stop = stop_base
        elif isinstance(stop_base, CharRange):
            stop = stop_base.stop
        else:
            stop = stop_base.contents

        start_len = len(start) if start else 0
        stop_len = len(stop) if stop else 0

        if start_len != 1 or stop_len != 1:
            raise ValueError(f"rgx.Chars.to can be used only on literals of length 1, got [{start_len} chars].to([{stop_len} chars])")

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

class ReversedChars(RegexPattern):
    def __init__(self, contents: Sequence[CharType]):
        self.contents = list(merge_chars(contents))

    def render(self) -> StrGen:
        yield "["
        yield "^"    
        for char in self.contents:
            if isinstance(char, (Literal, CharRange)):
                yield from char.render()
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

class CharRange:
    def __init__(self, start: Optional[str], stop: Optional[str]):
        self.start = start
        self.stop = stop
        if not (start or stop):
            raise ValueError("Cannot create a character range with no data. Use rgx.meta.ANY instead")

    def render(self) -> StrGen:
        if self.start:
            yield re.escape(self.start)
            if self.start == self.stop:
                return
        if self.start and self.stop:
            diff = ord(self.stop) - ord(self.start)
            if diff == 2:
                yield chr(ord(self.stop) - 1)
            elif diff > 2:
                yield "-"
        else:
            yield "-"
        if self.stop:
            yield re.escape(self.stop)

    def is_single_char(self) -> bool:
        return self.start is not None and self.start == self.stop

@overload
def char_range(start: Optional[str], stop: str) -> Chars:
    ...
@overload
def char_range(start: str, stop: None = None) -> Chars:
    ...
@overload
def char_range(start: None = None, stop: None = None) -> NoReturn:
    ...
@overload
def char_range(start: Optional[str], stop: Optional[str]) -> Chars:
    ...

def char_range(start: Optional[str] = None, stop: Optional[str] = None) -> Chars:
    """
    
    Use this for character ranges (e.g. `[a-z]`)

    Can be combined with other Chars istances (or lists) using |

    `start` and `stop` are inclusive

    """

    return Chars([CharRange(start, stop)])


class Concat(RegexPattern):
    priority = 2 * priority_step
    def __init__(self, *contents: AnyRegexPattern) -> None:
        self.contents = [respect_priority(part, self.priority) for part in contents]

    def __add__(self, other: AnyRegexPattern) -> Concat:
        return Concat(*self.contents, other)

    def render(self) -> StrGen:
        for part in self.contents:
            yield from part.render()


class Option(RegexPattern):
    priority = 0 * priority_step
    def __init__(self, *alternatives: AnyRegexPattern):
        self.alternatives = [respect_priority(alternative, self.priority) for alternative in alternatives]

    def render(self) -> StrGen:
        if not self.alternatives:
            return
        yield from self.alternatives[0].render()
        for alternative in self.alternatives[1:]:
            yield "|"
            yield from alternative.render()

    def __or__(self, other: AnyRegexPattern) -> Option:
        return Option(*self.alternatives, other)

    def __ror__(self, other: AnyRegexPattern) -> Option:
        return Option(other, *self.alternatives)


class LocalFlags(RegexPattern):
    def __init__(self, contents: AnyRegexPattern, flags: str):
        self.contents = pattern(contents)
        self.flags = flags

    def render(self) -> StrGen:
        yield "(?"
        yield self.flags
        yield ":"
        yield from self.contents.render()
        yield ")"


class GlobalFlags(GroupBase):
    prefix = "?"

    def __init__(self, contents: str):
        self.contents = Literal(contents)


class Range(RegexPattern):
    priority: int = 3 * priority_step
    def __init__(self, *contents: AnyRegexPattern, min_count: int = 0, max_count: Optional[int] = None, lazy: bool = False) -> None:
        self.contents = respect_priority(contents, self.priority + 1)
        self.min_count = min_count
        self.max_count = max_count
        self.lazy = lazy

        if self.max_count is not None and self.min_count > self.max_count:
            self.min_count, self.max_count = self.max_count, self.min_count

        if self.min_count < 0:
            raise ValueError("Quantifier lower bound cannot be less than 0")

        if self.max_count is not None and self.max_count < 0:
            raise ValueError("Quantifier upper bound cannot be less than 0")
        
        if max_count is not None and min_count > max_count:
            min_count, max_count = max_count, min_count

    def or_more(self) -> Range:
        return Range(self.contents, min_count=self.min_count, lazy=self.lazy)

    def __pos__(self) -> Range:
        return self.or_more()

    def or_less(self) -> Range:
        return Range(self.contents, min_count=0, max_count=self.max_count, lazy=self.lazy)

    def __neg__(self) -> Range:
        return self.or_less()

    def to(self, count: int) -> Range:
        return Range(self.contents, min_count=self.min_count, max_count=count, lazy=self.lazy)

    def __rshift__(self, count: int) -> Range:
        return self.to(count)

    def render_quantifier(self) -> StrGen:
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


    def render(self) -> StrGen:
        yield from self.contents.render()

        if self.min_count == self.max_count == 1:
            return

        yield from self.render_quantifier()

        if self.lazy and self.min_count != self.max_count:
            yield "?"

    def many(self, lazy: bool = False):
        return Range(self.contents, min_count=self.min_count, max_count=None, lazy=self.lazy and lazy)

    def some(self, lazy: bool = False):
        return Range(self.contents, min_count=0, lazy=self.lazy and lazy)

    def maybe(self, lazy: bool = False):
        if self.min_count in {0, 1}:
            return Range(self.contents, min_count=0, max_count=self.max_count, lazy=self.lazy and lazy)
        return Range(self, min_count=0, max_count=1, lazy=lazy)

    def x_times(self, count: int, lazy: bool = False) -> Range:
        if self.min_count in {0, 1} or self.max_count is None:
            return Range(
                self.contents, 
                min_count=self.min_count * count, 
                max_count=self.max_count * count if self.max_count is not None else None, 
                lazy=self.lazy and lazy
            )
        return Range(self, min_count=count, max_count=count, lazy=lazy)

    def x_or_more_times(self, count: int, lazy: bool = False) -> Range:
        if self.min_count in {0, 1} or self.max_count is None:
            return Range(
                self.contents, 
                min_count=self.min_count * count, 
                max_count=None, 
                lazy=self.lazy and lazy
            )
        return Range(self, min_count=count, lazy=lazy)

    def x_or_less_times(self, count: int, lazy: bool = False) -> Range:
        if self.max_count is None:
            return self.contents.some()

        return Range(
            self.contents,
            min_count=0,
            max_count=self.max_count * count
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

    def render(self) -> StrGen:
        yield "(?P"
        if self.contents:
            yield "<"
            yield self.name
            yield ">"
            yield from self.contents.render()
        else:
            yield "="
            yield self.name
        yield ")"


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
    def __init__(self, group: int, true_option: AnyRegexPattern, false_option: AnyRegexPattern) -> None:
        self.group = group
        self.true_option = respect_priority(true_option, Option.priority + 1)
        self.false_option = respect_priority(false_option, Option.priority + 1)

    def render(self) -> StrGen:
        yield "(?("
        yield str(self.group)
        yield ")"
        yield from self.true_option.render()
        yield "|"
        yield from self.false_option.render()
        yield ")"


class Literal(RegexPattern):
    def __init__(self, contents: str) -> None:
        self.contents: str = contents
        if len(self.contents) != 1:
            self.priority = 2 * priority_step

    def to(self, other: str | Literal | Chars) -> Chars:
        return Chars([self]).to(other)

    def render(self) -> StrGen:
        yield re.escape(self.contents)


class UnescapedLiteral(Literal):
    """
    
    Unescaped literal. Renders into whatever is passed (as long as it is a string)

    """

    def render(self) -> StrGen:
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