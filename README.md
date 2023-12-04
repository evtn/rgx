[![wordstreamer badge](https://img.shields.io/badge/renderable-what?label=wordstreamer&color=%2333bb33)](https://github.com/evtn/wordstreamer)

Many people complain about unreadable and complex syntax of regular expressions.  
Many others complain about how they can't remember all constructs and features.

`rgx` solves those problems: it is a straightforward regexp builder. It also places non-capturing groups where needed to respect intended operator priority.  
It can produce a regular expression string to use in `re.compile` or any other regex library of your choice.

In other words, with `rgx` you can build a regular expression from parts, using straightforward and simple expressions.

## Installation

`pip install rgx`

That's it.

## Basic usage

### Hello, regex world

```python
from rgx import pattern, meta
import re

separator = meta.WHITESPACE.some() + (meta.WHITESPACE | ",") + meta.WHITESPACE.some()

# matches "hello world", "hello, world", "hello            world", "hello,world", "hello ,  world"
hello_world = pattern((
    "hello",
    separator,
    "world"
)) # (?:hello(?:\s)*(?:\s|,)(?:\s)*world)

re.compile(
    hello_world.render_str("i") # global flag (case-insensitive)
)

```

### Match some integers

this regex will match valid Python integer literals:

```python
from rgx import pattern
import re

nonzero = pattern("1").to("9") # [1-9]
zero = "0"
digit = zero | nonzero # [0-9]
integer = zero | (nonzero + digit.some()) # 0|[1-9][0-9]*

int_regex = re.compile(str(integer))

```

...or this one:

```python
from rgx import pattern, meta
import re

nonzero = pattern("1").to("9") # [1-9]
digit = meta.DIGIT # \d
integer = digit | (nonzero + digit.some()) # \d|[1-9]\d*

int_regex = re.compile(str(integer))

```

## Quickstart

_in this readme, `x` means some pattern object. Occasionaly, `y` is introduced to mean some other pattern object (or literal)_

### Literals and pattern objects

`rgx` operates mostly on so-called "pattern objects" — `rgx.entities.RegexPattern` istances.  
Your starting point would be `rgx.pattern` — it creates pattern objects from literals (and from pattern objects, which doesn't make a lot of sense).

-   `rgx.pattern(str, escape: bool = True)` creates a literal pattern — one that exactly matches given string. If you want to disable escaping, pass `escape=False`
-   `rgx.pattern(tuple[AnyRegexPattern])` creates a non-capturing group of patterns (nested literals will be converted too)
-   `rgx.pattern(list[str])` creates a character class (for example, `rgx.pattern(["a", "b", "c"])` creates pattern `[abc]`, that matches any character of those in brackets)
    -   Same can be achieved by `rgx.pattern("a").to("c")` or `rgx.pattern("a") | "b" | "c"`

Most operations with pattern objects support using Python literals on one side, for example: `rgx.pattern("a") | b` would produce `[ab]` pattern object (specifically, `rgx.entities.Chars`)

### Rendering patterns

```python

from rgx import pattern

x = pattern("one")
y = pattern("two")
p = x | y

rendered_with_str = str(p) # "one|two"
rendered_with_method = p.render_str() # "one|two"
rendered_with_method_flags = p.render_str("im") # (?im)one|two
```

### Capturing Groups

```python
from rgx import pattern, reference, named

x = pattern("x")

print(x.capture()) # (x)

print(reference(1)) # \1


named_x = x.named("some_x") # x.named(name: str)

print(named_x) # (?P<some_x>x)

named_x_reference = named("some_x")

print(named_x_reference) # (?P=x)

```

To create a capturing group, use `x.capture()`, or `rgx.reference(group: int)` for a reference.  
To create a named capturing group, use `rgx.named(name: str, x)`, or `rgx.named(name: str)` for a named reference.

### Character classes

```python
from rgx import pattern, meta


az = pattern("a").to("z") # rgx.Chars.to(other: str | Literal | Chars)
print(az) # [a-z]

digits_or_space = pattern(["1", "2", "3", meta.WHITESPACE])
print(digits_or_space) # [123\s]

print(az | digits_or_space) # [a-z123\s]


print( # rgx.Chars.reverse(self)
    (az | digits_or_space).reverse() # [^a-z123\s]
)

```

#### Excluding characters

If you have two instances of Chars (or compatible literals), you can exclude one from another:

```python
from rgx import pattern

letters = pattern("a").to("z") | pattern("A").to("Z") # [A-Za-z]
vowels = pattern(list("aAeEiIoOuU")) # [AEIOUaeiou]
consonants = letters.exclude(vowels) # [BCDFGHJ-NP-TV-Zbcdfghj-np-tv-z]
```

### Conditional pattern

```python
from rgx import pattern, conditional

x = pattern("x")
y = pattern("y")
z = pattern("z")

capture = x.capture()

# (x)(?(1)y|z)
print(
    capture + conditional(1, y, z)
)
```

### Repeating patterns

If you need to match a repeating pattern, you can use `pattern.repeat(count, lazy)`:

```python
a = pattern("a")

a.repeat(5)                      # a{5}
# or
a * 5                            # a{5}, multiplication is an alias for .repeat

a.repeat(5).or_more()            # a{5,}
a.repeat(5).or_less()            # a{,5}

a.repeat_from(4).to(5)           # a{4, 5}, .repeat_from is just an alias for .repeat
# or
a.repeat(4) >> 5                 # a{4, 5}

a.repeat(1).or_less()            # a?
# or
-a.repeat(1)                     # a?
# or
a.maybe()                        # a?

a.repeat(1).or_more()            # a+
# or
+a.repeat(1)                     # a+
# or
+a                               # a+
# or
a.many()                         # a+

a.repeat(0).or_more()            # a*
# or
+a.repeat(0)                     # a*
# or
a.some()                         # a*
# or (what)
+-(a * 38)                       # a*
```

Here's what's going on:  
`pattern.repeat(count, lazy)` returns a `{count, count}` `Range` object  
`pattern * count` is the same as `pattern.repeat(count, False)`

`Range` implements `or_more`, `or_less` and `to` methods:

-   `Range.or_more()` [or `+Range`] moves (on a copy) upper bound of range to infinity (actually `None`)
-   `Range.or_less()` [or `-Range`] moves (on a copy) lower bound of range to 0
-   `Range.to(count)` [or `Range >> count` (right shift)] replaces upper bound with given number

Also, RegexPattern implements unary plus (`+pattern`) as an alias for `pattern.many()`

## Docs

### Pattern methods

#### `pattern.render_str(flags: str = '') -> str`

Renders given pattern into a string with specified global flags.

---

#### `pattern.set_flags(flags: str) -> LocalFlags`

This method adds local flags to given pattern

```python
x.flags("y") # "(?y:x)"
```

---

#### `pattern.concat(other: AnyRegexPattern) -> Concat`

Use to match one pattern and then another.

`A.concat(B)` is equivalent to `A + B` (works if either A or B is a RegexPart object, not a Python literal)

```python
x.concat(y) # "xy"
x + y # "xy"
```

---

#### `pattern.option(other: AnyRegexPattern) -> Chars | ReversedChars | Option`

Use to match either one pattern or another.

`A.option(B)` is equivalent to `A | B` (if either A or B is a RegexPart object, not a Python literal)

```python
x.option(y) # "x|y"
x | y # "x|y"
```

---

#### `pattern.many(lazy: bool = False) -> Range`

Use this for repeating patterns (one or more times)

When not lazy, matches as many times as possible, otherwise matches as few times as possible.

```python
x.many() # "x+"
x.many(True) # "x+?"
```

---

#### `pattern.some(lazy: bool = False) -> Range`

Use this for repeating optional patterns (zero or more times)

When not lazy, matches as many times as possible, otherwise matches as few times as possible.

```python
x.some() # "x*"
x.some(True) # "x*?"
```

---

#### `pattern.maybe(lazy: bool = False) -> Range`

Use this for optional patterns (zero or one times)

When not lazy, matches as many times as possible, otherwise matches as few times as possible.

```python
x.maybe() # "x?"
x.maybe(True) # "x??"
```

---

#### `pattern.x_or_less_times(count: int, lazy: bool = False) -> Range`

Use this to match pattern x or less times (hence the name).

When not lazy, matches as many times as possible, otherwise matches as few times as possible.

```python
x.x_or_less_times(5) # "x{,5}"
x.x_or_less_times(5, True) # "x{,5}?"
```

---

#### `pattern.x_or_more_times(count: int, lazy: bool = False) -> Range`

Use this to match pattern x or more times (hence the name).

When not lazy, matches as many times as possible, otherwise matches as few times as possible.

```python
x.x_or_more_times(5) # "x{5,}"
x.x_or_more_times(5, True) # "x{5,}?"
```

---

#### `pattern.x_times(count: int, lazy: bool = False) -> Range`

Use this to match pattern exactly x times (hence the name).

When not lazy, matches as many times as possible, otherwise matches as few times as possible.

```python
x.x_times(5) # "x{5}"
x.x_times(5, True) # "x{5}?"
x.repeat(5) # x{5}
```

---

#### `pattern.between_x_y_times(min_count: int, max_count: int, lazy: bool = False) -> Range`

Use this to match pattern between x and y times, inclusive (hence the name).

When not lazy, matches as many times as possible, otherwise matches as few times as possible.

```python
x.between_x_y_times(5, 6) # "x{5,6}"
x.between_x_y_times(5, 6, True) # "x{5,6}?"
```

---

#### `pattern.lookahead(other: RegexPattern) -> Concat`

Use this to indicate that given pattern occurs before some another pattern (lookahead).

In other words, `x.lookahead(y)` matches a pattern `x` only if there is `y` after it

Lookahead pattern won't be captured.

```python
x.lookahead(y) # x(?=y)
x.before(y) # x(?=y)
```

---

#### `pattern.negative_lookahead(other) -> Concat`

Use this to indicate that given pattern doesn't occur before some another pattern (negative lookahead).

In other words, `x.negative_lookahead(y)` matches a pattern `x` only if there is no `y` after it

Lookahead pattern won't be captured.

```python
x.negative_lookahead(y) # x(?!y)
x.not_before(y) # x(?!y)
```

---

#### `pattern.lookbehind(other: RegexPattern) -> Concat`

Use this to indicate that given pattern occurs after some another pattern (lookbehind).

In other words, `x.lookbehind(y)` matches a pattern `x` only if there is `y` before it

Lookbehind pattern won't be captured.

```python
x.lookbehind(y) # (?<=y)x
x.after(y) # (?<=y)x
```

---

#### `pattern.negative_lookbehind(other) -> Concat`

Use this to indicate that given pattern goes before some another pattern (negative lookbehind).

In other words, `x.negative_lookbehind(y)` matches a pattern `x` only if there is NO `y` before it

Lookbehind pattern won't be captured.

```python
x.negative_lookbehind(y) # (?<!y)x
x.not_after(y) # (?<!y)x
```

---

#### `pattern.capture() -> Group`

Use this to make a capturing group out of pattern.

```python
x.capture() # (x)
```

### Meta

`rgx.meta` is a collection of different meta-sequences and anchors:

```python
meta.WORD_CHAR = UnescapedLiteral(r"\w")
meta.NON_WORD_CHAR = UnescapedLiteral(r"\W")
meta.DIGIT = UnescapedLiteral(r"\d")
meta.NON_DIGIT = UnescapedLiteral(r"\D")
meta.WHITESPACE = UnescapedLiteral(r"\s")
meta.NON_WHITESPACE = UnescapedLiteral(r"\S")
meta.WORD_BOUNDARY = UnescapedLiteral(r"\b")
meta.NON_WORD_BOUNDARY = UnescapedLiteral(r"\B")
meta.ANY = UnescapedLiteral(".")
meta.NEWLINE = UnescapedLiteral(r"\n")
meta.CARRIAGE_RETURN = UnescapedLiteral(r"\r")
meta.TAB = UnescapedLiteral(r"\t")
meta.NULL_CHAR = UnescapedLiteral(r"\0")
meta.STRING_START = UnescapedLiteral("^")
meta.STRING_END = UnescapedLiteral("$")
```

Also `rgx.meta.CHAR_ESCAPE(char_number: int)` is available:

```python
from rgx import meta

print(meta.CHAR_ESCAPE(32)) # \x20
print(meta.CHAR_ESCAPE(320)) # \u0140
print(meta.CHAR_ESCAPE(320000)) # \U0004e200

```

### Unicode meta

`rgx.unicode_meta` is a collection of functions and constants, mostly for `\p` and `\P` usage:

Functions:

```python
unicode_meta.PROPERTY(value: str) # renders into `\p{value}` (any character with property specified by value, e.g. `PROPERTY("Ll") -> \p{Ll}`)
unicode_meta.PROPERTY_INVERSE(value: str) # matches all characters *not* matched by corresponding `PROPERTY` (`\P{value}`)

unicode_meta.NAMED_PROPERTY(name: str, value: str) # renders into `\p{name=value}` and matches any character which property `name` equals `value`
unicode_meta.NAMED_PROPERTY_INVERSE(name: str, value: str) # same, but inverted (`\P{name=value}`)
```

Constants:

```python
unicode_meta.LETTER = PROPERTY("L")
unicode_meta.NON_LETTER = PROPERTY_INVERSE("L")

unicode_meta.WHITESPACE = PROPERTY("Z")
unicode_meta.NON_WHITESPACE = PROPERTY_INVERSE("Z")

unicode_meta.DIGIT = PROPERTY("Nd")
unicode_meta.NON_DIGIT = PROPERTY("Nd")
```

## Extending

You can extend generation by subclassing one of the classes of `rgx.entities` module.  
The one neccessary method to provide is `.render(self, context: rgx.Context)`. It should return an iterable of strings (e.g. `["something"]`).  
Built-in components (and this section) are using generators for that purpose, but you're free to choose whatever works for you.
For example, if you want to render a PCRE accept control verb - `(*ACCEPT)`, you can do it like this:

```python
from rgx.entities import RegexPattern, Concat
from rgx import pattern, Context
from typing import Iterable


class Accept(RegexPattern):
    def render(self, context: Context) -> Iterable[str]:
        yield "(*ACCEPT)"


def accept(self) -> Concat:
    return self + Accept()


RegexPattern.accept = accept

x = pattern("something").accept()
print(x) # something(*ACCEPT)
```

Or like this:

```python
from rgx.entities import RegexPattern, Concat
from rgx import pattern, Context
from typing import Iterable


class Accept(RegexPattern):
    def __init__(self, accepted_pattern: RegexPattern):
        self.accepted_pattern = accepted_pattern

    def render(self, context: Context) -> Iterable[str]:
        yield from accepted_pattern.render(context)
        yield "(*ACCEPT)"


def accept(self) -> Accept:
    return Accept(self)

RegexPattern.accept = accept

x = pattern("something").accept() # something(*ACCEPT)
```

### Priority

If your extension has to rely on some priority, you can use `respect_priority` function.  
Let's say you want to add a `x/y` operation, which does something (wow) and has prority between `a|b` and `ab` — so `a|b/cd` is the same as `a|(?:b/(?:cd))`.

```python
from rgx.entities import RegexPattern, Concat, Option, AnyRegexPattern, respect_priority, pattern, Context
from typing import Iterable

class MagicSlash(RegexPattern):
    priority = (Concat.priority + Option.priority) // 2 # let's take something in the middle

    def __init__(self, left: RegexPattern, right: RegexPattern):
        self.left = respect_priority(left, self.priority) # you need to wrap all parts of your expression in respect_priority()
        self.right = respect_priority(right, self.priority) # ...and pass your expression priority as a second argument

    def render(self, context: Context) -> Iterable[str]:
        yield from self.left.render(context)
        yield "/"
        yield from self.right.render(context)


def slash(self, other: AnyRegexPattern) -> MagicSlash: # AnyRegexPattern is either a RegexPattern instance or a Python literal
    return MagicSlash(self, other) # respect_priority already takes literals in consideration, so no extra actions needed

def rslash(self, other: AnyRegexPattern) -> MagicSlash: # other/self
    other = pattern(other)
    return other / self


RegexPattern.slash = slash
RegexPattern.__truediv__ = slash # / operator
RegexPattern.__rtruediv__ = rslash


a = pattern("a")
b = pattern("b")
c = pattern("c")
d = pattern("d")

print(
    (a | b) / (c + d) # [ab]/cd
)

print(
    ((a | b) / c) + d # (?:[ab]/c)d
)

print(
    a | (b / c) + d   # a|(?:b/c)d
)

```

## Common questions

### Difference between `(x, y)` and `x + y`

Previous examples used `()` and `+`, and the difference might not be so obvious.

-   `x + y` creates a concatenation of patterns (`rgx.entities.Concat`), with no extra characters apart from those of patterns
-   `x + y` can be used only if at least one of the operands is a pattern object (that is, created with one of `rgx` functions or is one of `rgx` constants)
-   `x + y` produces a pattern object itself, so you won't need to call `pattern` on it to call pattern methods

-   `pattern((x, y))` creates a non-capturing group (`rgx.entities.NonCapturingGroup`): `pattern((x, y)).render_str()` -> `(?:xy)`
-   `(x, y)` can be used with any pattern-like literals or pattern objects
-   `(x, y)` is a tuple literal, so you can't use pattern methods on it directly or convert it into a complete expression (you need to use `rgx.pattern` on it first)
