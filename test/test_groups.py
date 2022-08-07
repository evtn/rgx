from rgx import pattern, conditional, named

a = pattern("a")
b = pattern("b")

class TestClass:
    def test_look_x(self):
        assert a.before(b).render_str() == "a(?=b)"
        assert a.after(b).render_str() == "(?<=b)a"

        assert a.not_before(b).render_str() == "a(?!b)"
        assert a.not_after(b).render_str() == "(?<!b)a"

    def test_comment(self):
        assert a.comment(" that's a!").render_str() == "a(?# that's a!)"

    def test_conditional(self):
        assert conditional(1, a, b).render_str() == "(?(1)a|b)"

    def test_group(self):
        assert a.capture().render_str() == "(a)"

    def test_named(self):
        assert named("a", b).render_str() == "(?P<a>b)"