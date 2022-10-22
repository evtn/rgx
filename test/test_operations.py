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
        # those are needed because one-char string produces Chars instance, thus making result render differently
        ab = pattern("ab")
        ac = pattern("ac")

        assert (ab | ac).render_str() == "ab|ac"
        assert (ab | "b").render_str() == "ab|b"
        assert ("a" | ac).render_str() == "a|ac"
        assert (ab | ac | ab).render_str() == "ab|ac|ab"
        assert ("a" | (ab | ac)).render_str() == "a|ab|ac"
        assert ab.option(ac).render_str() == (ab | ac).render_str()

    def test_char_option(self):
        assert (a | b).render_str() == "[ab]"
        assert (a | "b").render_str() == "[ab]"
        assert ("a" | b).render_str() == "[ab]"
        assert (a | b | a).render_str() == "[ab]"

    def test_quantifiers(self):
        assert a.many().render_str() == "a+"
        assert a.many(True).render_str() == "a+?"

        assert a.some().render_str() == "a*"
        assert a.some(True).render_str() == "a*?"

        assert a.maybe().render_str() == "a?"
        assert a.maybe(lazy=True).render_str() == "a??"

        assert a.maybe().maybe().maybe().maybe().maybe().maybe().maybe().maybe().render_str() == "a?"

        assert a.many().many().render_str() == "a+"

    def test_range_quantifier(self):
        assert a.repeat(5).or_less().render_str() == "a{,5}"
        assert a.x_or_less_times(5).render_str() == "a{,5}"

        assert a.repeat(5, lazy=True).or_less().render_str() == "a{,5}?"
        assert a.x_or_less_times(5, lazy=True).render_str() == "a{,5}?"

        assert a.repeat(5).or_more().render_str() == "a{5,}"
        assert a.x_or_more_times(5).render_str() == "a{5,}"

        assert a.repeat(5, lazy=True).or_more().render_str() == "a{5,}?"
        assert a.x_or_more_times(5, lazy=True).render_str() == "a{5,}?"

        assert a.repeat(5).render_str() == "a{5}"
        assert a.x_times(5).render_str() == "a{5}"

        assert a.repeat(5, lazy=True).render_str() == "a{5}"
        assert a.x_times(5, lazy=True).render_str() == "a{5}"

        assert a.repeat(4).to(5).render_str() == "a{4,5}"
        assert a.repeat_from(4).to(5).render_str() == "a{4,5}"
        assert a.between_x_y_times(4, 5).render_str() == "a{4,5}"

        # specific cases
        assert a.repeat(1).or_less().render_str() == "a?"
        assert a.repeat(1, True).or_less().render_str() == "a??"

        assert a.repeat(1).or_more().render_str() == "a+"
        assert a.repeat(1, lazy=True).or_more().render_str() == "a+?"

        assert a.repeat(0).or_more().render_str() == "a*"
        assert a.repeat(0, lazy=True).or_more().render_str() == "a*?"

        assert a.repeat(1).render_str() == "a"
        assert a.repeat(1, lazy=True).render_str() == "a"

        assert a.repeat(5).to(4).render_str() == "a{4,5}"

    def test_priority(self):
        ab = pattern("ab")
        ac = pattern("ac")

        assert ((ab | ac) + b).render_str() == "(?:ab|ac)b"
        assert ((a + b) | b).render_str() == "ab|b"
        assert (a + b).many().render_str() == "(?:ab)+"

    def test_flags(self):
        assert a.set_flags("i").render_str() == "(?i:a)"

    def test_empty_option(self):
        assert Option().render_str() == ""