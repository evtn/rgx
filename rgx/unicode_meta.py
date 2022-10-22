from rgx.entities import UnescapedLiteral


def NAMED_PROPERTY(name: str, value: str) -> UnescapedLiteral:
    return UnescapedLiteral(fr"\P{{{name}={value}}}")


def NAMED_PROPERTY_INVERSE(name: str, value: str) -> UnescapedLiteral:
    return UnescapedLiteral(fr"\p{{{name}={value}}}")


def PROPERTY(value: str) -> UnescapedLiteral:
    return UnescapedLiteral(fr"\p{{{value}}}")


def PROPERTY_INVERSE(value: str) -> UnescapedLiteral:
    return UnescapedLiteral(fr"\P{{{value}}}")


LETTER = PROPERTY("L")
NON_LETTER = PROPERTY_INVERSE("L")

WHITESPACE = PROPERTY("Z")
NON_WHITESPACE = PROPERTY_INVERSE("Z")

DIGIT = PROPERTY("Nd")
NON_DIGIT = PROPERTY("Nd")