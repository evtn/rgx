from rgx import pattern
from rgx.entities import Option

a = pattern("a")
b = pattern("b")

class TestClass:
    def test_concat(self):
        assert (a + "b").render_str() == "ab"
        assert ("b" + a).render_str() == "ba"
        assert (a + b).render_str() == "ab"
        assert (a + a + a).render_str() == "aaa"
        assert a.concat(b).concat(a).render_str() == (a + b + a).render_str()

    def test_option(self):
        assert (a | b).render_str() == "a|b"
        assert (a | "b").render_str() == "a|b"
        assert ("a" | b).render_str() == "a|b"
        assert (a | b | a).render_str() == "a|b|a"
        assert ("a" | (b | a)).render_str() == "a|b|a"
        assert a.option(b).render_str() == (a | b).render_str()

    def test_quantifiers(self):
        assert a.many().render_str() == "a+"
        assert a.many(True).render_str() == "a+?"

        assert a.some().render_str() == "a*"
        assert a.some(True).render_str() == "a*?"

        assert a.maybe().render_str() == "a?"
        assert a.maybe(True).render_str() == "a??"

    def test_range_quantifier(self):
        assert a.x_or_less_times(5).render_str() == "a{,5}"
        assert a.x_or_less_times(5, True).render_str() == "a{,5}?"

        assert a.x_or_more_times(5).render_str() == "a{5,}"
        assert a.x_or_more_times(5, True).render_str() == "a{5,}?"

        assert a.x_times(5).render_str() == "a{5}"
        assert a.x_times(5, True).render_str() == "a{5}"

        assert a.between_x_y_times(4, 5).render_str() == "a{4,5}"

        # specific cases
        assert a.x_or_less_times(1).render_str() == "a?"
        assert a.x_or_less_times(1, True).render_str() == "a??"

        assert a.x_or_more_times(1).render_str() == "a+"
        assert a.x_or_more_times(1, True).render_str() == "a+?"

        assert a.x_or_more_times(0).render_str() == "a*"
        assert a.x_or_more_times(0, True).render_str() == "a*?"

        assert a.x_times(1).render_str() == "a"
        assert a.x_times(1, True).render_str() == "a"

        assert a.between_x_y_times(5, 4).render_str() == "a{4,5}"

    def test_priority(self):
        assert ((a | b) + b).render_str() == "(?:a|b)b"
        assert ((a + b) | b).render_str() == "ab|b"
        assert a.many().many().render_str() == "(?:a+)+"
        assert (a + b).many().render_str() == "(?:ab)+"

    def test_flags(self):
        assert a.set_flags("i").render_str() == "(?i:a)"

    def test_chars_or(self):
        assert (pattern(["a"]) | "b").render_str() == "[a]|b"

    def test_empty_option(self):
        assert Option().render_str() == ""