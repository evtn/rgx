from rgx import pattern, char_range, reference, named
from rgx.entities import RegexPattern
import pytest

class TestClass:
    def test_literals(self):
        assert pattern("x").render_str() == "x"
        assert pattern(".").render_str() == "\\."
        assert pattern(".", escape=False).render_str() == "."
        assert pattern(("x", )).render_str() == "x"
        assert pattern(("x", "y")).render_str() == "(?:xy)"
        assert pattern(["x", "y"]).render_str() == "[xy]"

    def test_char_classes(self):

        onetwo_chars = pattern(["1", "2"])

        onetwo_list = ["1", "2"]
        onetwo_chars = pattern(onetwo_list)

        az_char_range = char_range("a", "z")

        assert az_char_range.render_str() == "[a-z]"
        assert az_char_range.reverse().render_str() == "[^a-z]"
        assert (onetwo_chars | az_char_range).render_str() == "[12a-z]"
        assert (onetwo_list | az_char_range).render_str() == "[12a-z]"

        assert char_range("a").render_str() == "[a-]"
        assert char_range(None, "z").render_str() == "[-z]"

        assert pattern(["-"]).render_str() == "[\\-]"

        a = pattern("a")
        assert repr(a) == a.render_str()

        with pytest.raises(ValueError):
            char_range()

    def test_references(self):
        assert reference(1).render_str() == "\\1"
        assert named("x").render_str() == "(?P=x)"

    def test_flags(self):
        assert pattern("x").render_str("i") == "(?i)x"

    def test_that_render_on_regex_pattern_is_not_implemented_i_know_this_is_stupid_but_still(self):
        assert RegexPattern().render() == NotImplemented