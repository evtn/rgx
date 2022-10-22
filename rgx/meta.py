from rgx.entities import UnescapedLiteral


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
STRING_START = UnescapedLiteral("^")
STRING_END = UnescapedLiteral("$")

def CHAR_ESCAPE(char_number: int):
    try:
        chr(char_number)
    except ValueError:
        raise ValueError(f"Invalid character: {char_number}")
    prefix = ["x", "u", "U"][(char_number > 255) + (char_number > 65535)]
    length = {"x": 2, "u": 4, "U": 8}[prefix]
    return UnescapedLiteral(f"\\{prefix}{char_number:0{length}x}")