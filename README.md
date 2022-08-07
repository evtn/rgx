Many people complain about unreadable and complex syntax of regular expressions.    
Many others complain about how they can't remember all constructs and features.

`rgx` solves those problems: it is a straightforward regexp builder. It also places parens where needed to respect intended operator priority.    
It can produce a regular expression string to use in `re.compile` or any other regex library of your choice.    


## Installation

`pip install rgx`

That's it.

## Quickstart

*in this readme, `x` means some pattern object. Occaasionaly, `y` is introduced to mean some other pattern object (or literal)*

### Literals and pattern objects

`rgx` operates mostly on so-called "pattern objects" — `rgx.entities.RegexPattern` istances.    
Your starting point would be `rgx.pattern` — it creates pattern objects from literals (and from pattern objects, which doesn't make a lot of sense).

- `rgx.pattern(str, escape: bool = True)` creates a literal pattern — one that exactly matches given string. If you want to disable escaping, pass `escape=False`
- `rgx.pattern(tuple[AnyRegexPattern])` creates a non-capturing group of patterns (nested literals will be converted too)
- `rgx.pattern(list[str])` creates a character class (for example, `rgx.pattern(["a", "b", "c"])` creates pattern `[abc]`, that matches any character of those in brackets)

Most operations with pattern objects support using Python literals on one side, for example: `rgx.pattern("a") | b` would produce `a|b` pattern object (specifically, `rgx.entities.Option`)    

### Rendering patterns

```python

import rgx

x = rgx.pattern("x")
pattern = x | x

rendered_with_str = str(pattern) # "x|x"
rendered_with_method = pattern.render_str() # "x|x"
rendered_with_method_flags = pattern.render_str("im") # (?im)x|x
```    

### Capturing Groups

```python
import rgx

x = rgx.pattern("x")

print(x.capture()) # (x)

print(rgx.reference(1)) # \1


named_x = x.named("some_x") # x.named(name: str)

print(named_x) # (?P<some_x>x)

named_x_reference = rgx.named("some_x")

print(named_x_reference) # (?P=x)

```

To create a capturing group, use `x.capture()`, or `rgx.reference(group: int)` for a named reference.    
To create a named capturing group, use `rgx.named(name: str, x)`, or `rgx.named(name: str)` for a named reference.    

### Character classes

```python
import rgx


az = rgx.char_range("a", "z") # rgx.char_range(start?: str, stop?: str)
print(az) # [a-z]

digits = rgx.pattern(["1", "2", "3"]) 
print(digits) # [123]

print(az | digits) # [a-z123]

# [^a-z123]
print(
    (az | digits).reverse() # rgx.entities.Chars.reverse(self)
)

```  

---

For a conditional pattern, use `rgx.conditional(group: int, x, y)` (where `x` matches if `group` has matched, and `y` otherwise)

## Basic usage

### Hello, regex world

```python
import rgx
import re

word = rgx.meta.WORD_CHAR.many().capture() # (\w+), a capturing group
comma = rgx.pattern(",").maybe()

regex = rgx.pattern((
    "hello",
    comma,
    rgx.meta.WHITESPACE,
    (
        word + rgx.meta.WHITESPACE
    ).maybe(),
    "world"
)) # (?:hello,?\s(?:(\w*)\s)?world)

re.compile(
    regex.render_str("i") # global flag (case-insensitive)
)

```

### Match some integers

this regex will match valid Python integer literals:

```python
import rgx
import re

nonzero = rgx.char_range("1", "9") # [1-9]
zero = "0"
digit = zero | nonzero # 0|[1-9]
integer = zero | (nonzero + digit.some()) # 0|[1-9](?:0|[1-9])*

int_regex = re.compile(str(integer))

```

...or this one:

```python
import rgx
import re

nonzero = rgx.char_range("1", "9") # [1-9]
digit = rgx.meta.DIGIT # \d
integer = digit | (nonzero + digit.some()) # \d|[1-9]\d*

int_regex = re.compile(str(integer))

```

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

#### `pattern.option(other: AnyRegexPattern) -> Option`

Use to match either one pattern or another.

`A.option(B)` is equivalent to `A | B` (if either A or B is a RegexPart object, not a Python literal)

```python
x.option(y) # "x|y"
x | y # "x|y"
```

---

#### `pattern.many(lazy: bool = False) -> Many`

Use this for repeating patterns (one or more times)

When not lazy, matches as many times as possible, otherwise matches as few times as possible.

```python
x.many() # "x+"
x.many(True) # "x+?"
```

---

#### `pattern.some(lazy: bool = False) -> Some`

Use this for repeating optional patterns (zero or more times)

When not lazy, matches as many times as possible, otherwise matches as few times as possible.

```python
x.some() # "x*"
x.some(True) # "x*?"
```

---

#### `pattern.maybe(lazy: bool = False) -> Maybe`

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

Use this to indicate that given pattern occurs after some another pattern (lookahead).

In other words, `x.lookbehind(y)` matches a pattern `x` only if there is `y` before it

Lookbehind pattern won't be captured.

```python
x.lookbehind(y) # (?<=y)x
x.after(y) # (?<=y)x
```

---

#### `pattern.negative_lookbehind(other) -> Concat`

Use this to indicate that given pattern goes before some another pattern (lookahead).

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

## Common questions

### Difference between `(x, y)` and `x + y`

Previous examples used `()` and `+`, and the difference might not be so obvious.    

- `x + y` creates a concatenation of patterns (`rgx.entities.Concat`), with no extra characters apart from those of patterns
- `x + y` can be used only if at least one of the operands is a pattern object (that is, created with one of `rgx` functions or is one of `rgx` constants)
- `x + y` produces a pattern object itself, so you won't need to call `pattern` on it to call pattern methods

- `pattern((x, y))` creates a non-capturing group (`rgx.entities.NonCapturingGroup`): `pattern((x, y)).render_str()` -> `(?:xy)`
- `(x, y)` can be used with any pattern-like literals or pattern objects
- `(x, y)` is a tuple literal, so you can't use pattern methods on it directly or convert it into a complete expression (you need to use `rgx.pattern` on it first)