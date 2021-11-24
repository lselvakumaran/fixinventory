import pytest

from core.query.model import P, Query, AllTerm, IsTerm
from core.query.query_parser import parse_query


def simple_reference() -> None:
    # only kind
    Query.by("ec2")

    # equality
    Query.by(P.of_kind("ec2") & (P("simple") == "hallo"))
    Query.by(P.of_kind("ec2") & (P("simple") != "hallo"))

    # regex
    Query.by(P.of_kind("ec2") & P("simple").matches("^some.regex[a-d]+$"))
    Query.by(P.of_kind("ec2") & P("simple").not_matches("^some.regex[a-d]+$"))

    # comparator
    Query.by(P.of_kind("ec2") & (P("num") > 23))
    Query.by(P.of_kind("ec2") & (P("num") >= 23))
    Query.by(P.of_kind("ec2") & (P("num") == 23))
    Query.by(P.of_kind("ec2") & (P("num") <= 23))
    Query.by(P.of_kind("ec2") & (P("num") < 23))

    # in set
    Query.by(P.of_kind("ec2") & P("num").is_in([1, 2, 5]))
    Query.by(P.of_kind("ec2") & P("num").is_not_in([1, 2, 5]))

    # array: all above operators are available
    Query.by(P.of_kind("ec2") & (P.array("some.array").for_all() > 12.23))
    Query.by(P.of_kind("ec2") & (P.array("some.array").for_any().is_in([1, 2, 3])))
    Query.by(P.of_kind("ec2") & (P.array("some.array").for_none() == 5))

    # call a function
    Query.by(P.function("in_subnet").on("ip", "1.2.3.4/16"))

    # refine with multiple predicates (all predicates have to match)
    Query.by(P.of_kind("ec2") & P("a").ge(1), P("b") == 2, P("c").matches("aaa"))


def test_simple_query() -> None:
    a = (
        Query.by("ec2", P("cpu") > 4, (P("mem") < 23) | (P("mem") < 59))
        .traverse_out()
        .filter(P("some.int.value") < 1, P("some.other") == 23)
        .traverse_out()
        .filter(P("active") == 12, P.function("in_subnet").on("ip", "1.2.3.4/32"))
    )

    assert (
        str(a) == '((is("ec2") and cpu > 4) and (mem < 23 or mem < 59)) --> '
        "(some.int.value < 1 and some.other == 23) --> "
        '(active == 12 and in_subnet(ip, "1.2.3.4/32"))'
    )


def test_simplify() -> None:
    # some_criteria | all => all
    assert str((IsTerm(["test"]) | AllTerm()).simplify()) == "all"
    # some_criteria & all => some_criteria
    assert str((IsTerm(["test"]) & AllTerm()).simplify()) == 'is("test")'
    # also works in nested setup
    q = Query.by(AllTerm() & ((P("test") == True) & (IsTerm(["test"]) | AllTerm()))).simplify()
    assert (str(q)) == "test == true"


def test_combine() -> None:
    query1 = Query.by(P("test") == True).traverse_out().combine(Query.by("foo")).combine(Query.by("bla"))
    assert str(query1) == 'test == true --> (is("foo") and is("bla"))'
    query2 = (
        Query.by(P("test") == True)
        .traverse_out()
        .combine(Query.by("foo").traverse_out())
        .combine(Query.by("bla").traverse_out())
    )
    assert str(query2) == 'test == true --> is("foo") --> is("bla") -->'
    query3 = (
        Query.by(P("test") == True)
        .traverse_out()
        .filter("boo")
        .traverse_out()
        .filter("bar")
        .combine(Query.by("foo"))
        .combine(Query.by("bla"))
    )
    assert str(query3) == 'test == true --> is("boo") --> ((is("bar") and is("foo")) and is("bla"))'
    query4 = Query.by("a").with_limit(10).combine(Query.by("b").with_limit(2))
    assert query4.current_part.limit == 2  # minimum is taken
    with pytest.raises(AttributeError):
        # can not combine 2 aggregations
        parse_query("aggregate(sum(1)): is(a)").combine(parse_query("aggregate(sum(1)): is(a)"))
    with pytest.raises(AttributeError):
        # can not combine 2 with statements
        parse_query("is(foo) with(empty, -->)").combine(parse_query("is(bla) with(empty, -->)"))


def test_on_section() -> None:
    query = 'cpu > 4 and (mem < 23 or mem < 59) with(any, <-- name == "test") sort mem --> a<1 and b==23 sort foo'
    on_section = (
        '(r.cpu > 4 and (r.mem < 23 or r.mem < 59)) with(any, <-- r.name == "test") sort r.mem asc --> '
        "(r.a < 1 and r.b == 23) sort r.foo asc"
    )
    assert str(parse_query(query).on_section("r")) == on_section
