from __future__ import annotations
from collections.abc import Iterable, Sequence

from typing import Generator, Optional, Union, overload, List

import itertools
import re

StrGen = Generator[str, None, None]
CharType = Union[str, "CharRange"]
LiteralPart = Union[tuple, List[str], str]
AnyRegexPattern = Union[LiteralPart, "RegexPattern"]

@overload
def pattern(literal: tuple, escape: bool = True) -> Union[RegexPattern, NonCapturingGroup]:
    ...
@overload
def pattern(literal: List[str], escape: bool = True) -> Chars:
    ...
@overload
def pattern(literal: RegexPattern, escape: bool = True) -> RegexPattern:
    ...
@overload
def pattern(literal: str, escape: bool) -> Union[UnescapedLiteral, Literal]:
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
    priority: int = 999
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

        Render:

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

        Render:

        ```python
        x.concat(y) # "xy"
        x + y # "xy"
        ```
        """
        return self + other

    def __or__(self, other: AnyRegexPattern) -> Union[Option, Chars]:
        return Option(self, other)

    def __ror__(self, other: AnyRegexPattern) -> Union[Option, Chars]:
        return Option(other, self)

    def option(self, other: AnyRegexPattern) -> Union[Option, Chars]:
        """
        Use to match either one pattern or another.

        `A.option(B)` is equivalent to `A | B` (if either A or B is a RegexPart object, not a Python literal)

        Render:

        ```python
        x.option(y) # "x|y"
        x | y # "x|y"
        ```
        """
        return self | other

    def many(self, lazy: bool = False) -> Many:
        """
        Use this for repeating patterns (one or more times)

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.
        
        Render:

        ```python
        x.many() # "x+"
        x.many(True) # "x+?"
        ```
        """
        return Many(self, lazy=lazy)

    plus = many

    def some(self, lazy: bool = False) -> Some:
        """
        Use this for repeating optional patterns (zero or more times)

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        Render:

        ```python
        x.some() # "x*"
        x.some(True) # "x*?"
        ```
        """
        return Some(self, lazy=lazy)

    star = some

    def maybe(self, lazy: bool = False) -> Maybe:
        """
        Use this for optional patterns (zero or one times)

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        Render:
        
        ```python
        x.maybe() # "x?"
        x.maybe(True) # "x??"
        ```
        """
        return Maybe(self, lazy=lazy)

    optional = maybe

    def x_or_less_times(self, count: int, lazy: bool = False) -> Range:
        """
        
        Use this to match pattern x or less times (hence the name).

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        Render:
        
        ```python
        x.x_or_less_times(5) # "x{,5}"
        x.x_or_less_times(5, True) # "x{,5}?"
        ```
        """
        return Range(self, max_count=count, lazy=lazy)

    def x_or_more_times(self, count: int, lazy: bool = False) -> Range:
        """
        
        Use this to match pattern x or more times (hence the name).

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        Render:
        
        ```python
        x.x_or_more_times(5) # "x{5,}"
        x.x_or_more_times(5, True) # "x{5,}?"
        ```
        """
        return Range(self, min_count=count, lazy=lazy)

    def x_times(self, count: int, lazy: bool = False) -> Range:
        """
        
        Use this to match pattern exactly x times (hence the name).

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        Render:
        
        ```python
        x.x_times(5) # "x{5}"
        x.x_times(5, True) # "x{5}?"
        ```
        """
        return Range(self, min_count=count, max_count=count, lazy=lazy)

    def between_x_y_times(self, min_count: int, max_count: int, lazy: bool = False) -> Range:
        """
        
        Use this to match pattern between x and y times, inclusive (hence the name).

        When not lazy, matches as many times as possible, otherwise matches as few times as possible.

        Render:
        
        ```python
        x.between_x_y_times(5, 6) # "x{5,6}"
        x.between_x_y_times(5, 6, True) # "x{5,6}?"
        ```
        """
        return Range(self, min_count=min_count, max_count=max_count, lazy=lazy)

    def lookahead(self, other: RegexPattern) -> Concat:
        """
        Use this to indicate that given pattern occurs before some another pattern (lookahead).

        In other words, `x.lookahead(y)` matches a pattern `x` only if there is `y` after it

        Lookahead pattern won't be captured.

        Render:

        ```python
        x.lookahead(y) # x(?=y)
        x.before(y) # x(?=y)
        ```
        """
        return Concat(self, Lookahead(other))

    before = lookahead

    def negative_lookahead(self, other) -> Concat:
        """
        Use this to indicate that given pattern doesn't occur before some another pattern (negative lookahead).

        In other words, `x.negative_lookahead(y)` matches a pattern `x` only if there is no `y` after it

        Lookahead pattern won't be captured.

        Render:

        ```python
        x.negative_lookahead(y) # x(?!y)
        x.not_before(y) # x(?!y)
        ```
        """
        return Concat(self, NegativeLookahead(other))

    not_before = negative_lookahead

    def lookbehind(self, other: RegexPattern) -> Concat:
        """
        Use this to indicate that given pattern occurs after some another pattern (lookahead).

        In other words, `x.lookbehind(y)` matches a pattern `x` only if there is `y` before it

        Lookbehind pattern won't be captured.

        Render:

        ```python
        x.lookbehind(y) # (?<=y)x
        x.after(y) # (?<=y)x
        ```
        """
        return Concat(Lookbehind(other), self)

    after = lookbehind

    def negative_lookbehind(self, other) -> Concat:
        """
        Use this to indicate that given pattern goes before some another pattern (lookahead).

        In other words, `x.negative_lookbehind(y)` matches a pattern `x` only if there is NO `y` before it

        Lookbehind pattern won't be captured.

        Render:

        ```python
        x.negative_lookbehind(y) # (?<!y)x
        x.not_after(y) # (?<!y)x
        ```
        """
        return Concat(NegativeLookbehind(other), self)

    not_after = negative_lookbehind

    def comment(self, text: str) -> Concat:
        """ leaves a comment in expression (if needed for whatever reason) """
        return Concat(self, Comment(UnescapedLiteral(text.replace(")", "\\)"))))

    def capture(self) -> Group:
        """
        
        Use this to make a capturing group out of pattern.

        Render:

        ```python
        x.capture() # (x)
        ```
        """
        return Group(self)

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

class Chars(RegexPattern):
    def __init__(self, contents: Sequence[CharType], is_reversed: bool = False):
        self.contents = list(contents)
        self.is_reversed = is_reversed

    def render(self) -> StrGen:
        yield "["
        if self.is_reversed:
            yield "^"
        for char in self.contents:
            if isinstance(char, CharRange):
                yield from char.render()
            else:
                yield re.escape(char)
        yield "]"

    def reverse(self) -> Chars:
        return Chars(self.contents, not self.is_reversed)

    def __or__(self, other: AnyRegexPattern) -> Union[Option, Chars]:
        other = respect_priority(other, Option.priority)
        if isinstance(other, Chars) and self.is_reversed == other.is_reversed:
            return Chars([*self.contents, *other.contents], self.is_reversed)
        return Option(self, other)

    def __ror__(self, other: AnyRegexPattern) -> Union[Option, Chars]:
        other = respect_priority(other, Option.priority)
        return other | self

class CharRange:
    def __init__(self, start: Optional[str], stop: Optional[str]):
        self.start = start
        self.stop = stop
        if not (start or stop):
            raise ValueError("Cannot create a character range with no data. Use rgx.meta.ANY instead")

    def render(self) -> StrGen:
        if self.start:
            yield re.escape(self.start)
        yield "-"
        if self.stop:
            yield re.escape(self.stop)


def char_range(start: Optional[str] = None, stop: Optional[str] = None) -> Chars:
    """
    
    Use this for character ranges (e.g. `[a-z]`)

    Can be combined with other Chars istances (or lists) using |

    `start` and `stop` are inclusive

    """

    return Chars([CharRange(start, stop)])


class Concat(RegexPattern):
    priority = 2
    def __init__(self, *contents: AnyRegexPattern) -> None:
        self.contents = [respect_priority(part, self.priority) for part in contents]

    def __add__(self, other: AnyRegexPattern) -> Concat:
        return Concat(*self.contents, other)

    def render(self) -> StrGen:
        for part in self.contents:
            yield from part.render()


class Option(RegexPattern):
    priority = 0
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

class Quantifier(RegexPattern):
    priority = 3
    quantifier: str
    def __init__(self, *contents: AnyRegexPattern, lazy: bool = False) -> None:
        self.contents = respect_priority(contents, self.priority + 1)
        self.lazy = lazy

    def render(self) -> StrGen:
        yield from self.contents.render()
        yield self.quantifier
        if self.lazy:
            yield "?"

class Maybe(Quantifier):
    quantifier = "?"

class Some(Quantifier):
    quantifier = "*"
    
class Many(Quantifier):
    quantifier = "+"

class Range(Quantifier):
    def __init__(self, *contents: AnyRegexPattern, min_count: int = 0, max_count: Optional[int] = None, lazy: bool = False) -> None:
        self.contents = respect_priority(contents, self.priority + 1)
        self.lazy = lazy
        
        if max_count is not None and min_count > max_count:
            min_count, max_count = max_count, min_count
        if min_count == max_count:
            self.lazy = False # lazy doesn't make any sense with min_count == max_count

        # specific count optimizations
        if max_count is None:
            if not min_count:
                self.quantifier = "*"
                return
            elif min_count == 1:
                self.quantifier = "+"
                return

        if max_count == 1:
            if not min_count:
                self.quantifier = "?"
                return
            elif min_count == 1:
                self.quantifier = ""
                self.lazy = False
                return


        if min_count == max_count:
            self.quantifier = f"{{{min_count}}}"
        elif not min_count:
            self.quantifier = f"{{,{max_count}}}"
        elif not max_count:
            self.quantifier = f"{{{min_count},}}"
        else:
            self.quantifier = f"{{{min_count},{max_count}}}"

class NamedPattern(RegexPattern):
    """

    Named capturing group.

    If `contents` are omitted, generates a reference, otherwise a named group definition.

    Render:

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
        self.contents = contents

    def render(self) -> StrGen:
        yield re.escape(self.contents)


class UnescapedLiteral(RegexPattern):
    """
    
    Unescaped literal. Renders into whatever is passed (as long as it is a string)

    """

    def __init__(self, contents: str) -> None:
        self.contents: str = contents

    def render(self) -> StrGen:
        yield self.contents


class Meta:
    """
    A collection of special char sequences in form of UnescapedLiteral
    """
    WORD_CHAR = UnescapedLiteral(r"\w")
    NON_WORD_CHAR = UnescapedLiteral(r"\W")
    DIGIT = UnescapedLiteral(r"\d")
    NON_DIGIT = UnescapedLiteral(r"\D")
    WHITESPACE = UnescapedLiteral(r"\s")
    NON_WHITESPACE = UnescapedLiteral(r"\S")
    WORD_BOUNDARY = UnescapedLiteral(r"\b")
    NON_WORD_BOUNDARY = UnescapedLiteral(r"\B")
    ANY = UnescapedLiteral(".")
    NEWLINE = UnescapedLiteral(r"\n")
    CARRIAGE_RETURN = UnescapedLiteral(r"\r")
    TAB = UnescapedLiteral(r"\t")
    NULL_CHAR = UnescapedLiteral(r"\0")


def group_reference(group: int) -> UnescapedLiteral:
    """
    
    Renders into a group reference (backreference)
    E.g. if Group #1 is `(x|y)` and it has matched "x", `reference(1)` would match exactly "x", but not "y"

    Render:

    ```python
    rgx.reference(1) # \\1
    ```

    """
    return UnescapedLiteral(f"\\{group}")