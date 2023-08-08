from rgx.entities import UnescapedLiteral
from rgx import pattern, char_range


letter = char_range("a", "z") | char_range("A", "Z")
nonzero = char_range("1", "9")
digit = char_range("0", "9")
mark = pattern(["-", "_", ".", "!", "~", "*", "'", "(", ")"])
reserved = pattern([";", "/", "?", ":", "@", "&", "=", "+", "$", ","])
unreserved = letter | digit | mark

hex_char = digit | char_range("a", "f") | char_range("A", "F")
escaped = "%" + hex_char.x_times(2)

identifier = letter + (letter | digit | pattern(["+", "-", "."])).some()
scheme = identifier.named("scheme")

userinfo = (
    (unreserved | escaped | pattern([";", ":", "&", "=", "+", "$", ","]))
    .many()
    .named("userinfo")
)

domain = (letter | digit) + (
    (letter | digit | pattern(["-"])).some() + (letter | digit)
).maybe()

top_domain = (
    letter + ((letter | digit | pattern(["-"])).some() + (letter | digit)).maybe()
)

hostname = (domain + ".").some() + top_domain + pattern(".").maybe()

ip_number = (pattern("1").maybe() + nonzero.maybe() + digit) | (
    "2" + (char_range("0", "4") + digit | "5" + char_range("0", "5"))
)

ip4_address = (ip_number + ".").x_times(3) + ip_number
host = (hostname | ip4_address).named("host")

port = digit.some().named("port")

authority = ((userinfo + "@").maybe() + host + (":" + port).maybe()).named("authority")

pchar = unreserved | escaped | pattern([":", "@", "&", "=", "+", "$", ",", ";"])

param = pchar.some()
path_segment = param + (";" + param).some()
path_segment_nonempty = pchar.many() | param + (";" + param).many()
path_segments = path_segment.maybe() + ("/" + path_segment.maybe()).some()
no_authority_path = (path_segment_nonempty + "/" + path_segments).maybe()

path = ("/" + path_segments).named("path")

autority_with_path = "//" + authority + path.maybe()
no_authority_with_path = no_authority_path.named("path_noauthority")

qfchars = (pchar | pattern(["?", "/"])).some()

query = qfchars.named("query")
fragment = qfchars.named("fragment")

url = (
    scheme
    + ":"
    + (autority_with_path | no_authority_with_path)
    + ("?" + query).maybe()
    + (UnescapedLiteral("#") + fragment).maybe()
)

import re

url_regex = re.compile(str(url))


test_suites: dict[str, dict] = {
    "https://datatracker.ietf.org/doc/html/rfc3986?asd=213#section-3.4": {
        "scheme": "https",
        "authority": "datatracker.ietf.org",
        "userinfo": None,
        "host": "datatracker.ietf.org",
        "port": None,
        "path": "/doc/html/rfc3986",
        "path_noauthority": None,
        "query": "asd=213",
        "fragment": "section-3.4",
    },
    "http://http://http://@http://http://?http://#http://": {
        "scheme": "http",
        "authority": "http:",
        "userinfo": None,
        "host": "http",
        "port": "",
        "path": "//http://@http://http://",
        "path_noauthority": None,
        "query": "http://",
        "fragment": "http://",
    },
    "https://mail.python.org/archives/list/typing-sig@python.org/thread/66RITIHDQHVTUMJHH2ORSNWZ6DOPM367/#QYOBBLTWVSEWMFRRHBA2OPR5QQ4IMWOL": {
        "scheme": "https",
        "authority": "mail.python.org",
        "userinfo": None,
        "host": "mail.python.org",
        "port": None,
        "path": "/archives/list/typing-sig@python.org/thread/66RITIHDQHVTUMJHH2ORSNWZ6DOPM367/",
        "path_noauthority": None,
        "query": None,
        "fragment": "QYOBBLTWVSEWMFRRHBA2OPR5QQ4IMWOL",
    },
}


class TestClass:
    def test_url(self):
        for test_url, expected_result in test_suites.items():
            match = url_regex.fullmatch(test_url)

            assert match and match.groupdict() == expected_result
