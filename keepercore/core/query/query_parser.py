from dataclasses import replace
from functools import reduce

from parsy import string, Parser, regex

from core.model.graph_access import EdgeType
from core.parse_util import (
    lparen_p,
    lexeme,
    rparen_p,
    l_bracket_p,
    r_bracket_p,
    colon_p,
    comma_p,
    equals_p,
    true_p,
    false_p,
    dot_dot_p,
    float_p,
    integer_dp,
    variable_dp,
    literal_p,
    make_parser,
    whitespace,
    quoted_string_p,
    space_dp,
    json_value_p,
    variable_p,
    integer_p,
)
from core.query.model import (
    Predicate,
    CombinedTerm,
    IsTerm,
    Part,
    Navigation,
    Query,
    FunctionTerm,
    IdTerm,
    AggregateVariable,
    AggregateFunction,
    Aggregate,
    AllTerm,
    Sort,
    SortOrder,
)

operation_p = reduce(
    lambda x, y: x | y, [lexeme(string(a)) for a in ["<=", ">=", ">", "<", "==", "!=", "=~", "!~", "in", "not in"]]
)

function_p = reduce(lambda x, y: x | y, [lexeme(string(a)) for a in ["in_subnet", "has_desired_change"]])


preamble_prop_p = reduce(lambda x, y: x | y, [lexeme(string(a)) for a in ["edge_type", "merge_with_ancestors"]])


@make_parser
def predicate_term() -> Parser:
    name = yield variable_p
    op = yield operation_p
    value = yield json_value_p
    return Predicate(name, op, value, {})


@make_parser
def function_term() -> Parser:
    fn = yield function_p
    yield lparen_p
    name = yield variable_p
    args = yield (comma_p >> json_value_p).many()
    yield rparen_p
    return FunctionTerm(fn, name, args)


is_term = lexeme(string("is") >> lparen_p >> (quoted_string_p | literal_p) << rparen_p).map(IsTerm)
id_term = lexeme(string("id") >> lparen_p >> (quoted_string_p | literal_p) << rparen_p).map(IdTerm)
match_all_term = lexeme(string("all")).map(lambda _: AllTerm())
leaf_term_p = is_term | id_term | match_all_term | function_term | predicate_term

bool_op_p = lexeme(string("and") | string("or"))


@make_parser
def combined_term() -> Parser:
    left = yield simple_term_p
    result = left
    while True:
        op = yield bool_op_p.optional()
        if op is None:
            break
        right = yield simple_term_p
        result = CombinedTerm(result, op, right)
    return result


simple_term_p = (lparen_p >> combined_term << rparen_p) | leaf_term_p

# This can parse a complete term
term_parser = combined_term | simple_term_p


@make_parser
def range_parser() -> Parser:
    yield l_bracket_p
    start = yield integer_p
    has_end = yield (colon_p | comma_p | dot_dot_p).optional()
    maybe_end = yield integer_p.optional()
    yield r_bracket_p
    end = start if has_end is None else maybe_end if maybe_end is not None else Navigation.Max
    return start, end


edge_type_p = lexeme(regex("[A-Za-z][A-Za-z0-9_]*"))


@make_parser
def edge_definition() -> Parser:
    maybe_edge_type = yield edge_type_p.optional()
    maybe_range = yield range_parser.optional()
    parsed_range = maybe_range if maybe_range else (1, 1)
    return parsed_range[0], parsed_range[1], maybe_edge_type


out_p = lexeme(string("-") >> edge_definition << string("->")).map(
    lambda nav: Navigation(nav[0], nav[1], nav[2], "out")
)
in_p = lexeme(string("<-") >> edge_definition << string("-")).map(lambda nav: Navigation(nav[0], nav[1], nav[2], "in"))
in_out_p = lexeme(string("-") >> edge_definition << string("-")).map(
    lambda nav: Navigation(nav[0], nav[1], nav[2], "inout")
)
navigation_parser = out_p | in_p | in_out_p

pin_parser = lexeme(string("+")).optional().map(lambda x: x is not None)


@make_parser
def part_parser() -> Parser:
    term = yield term_parser
    yield whitespace
    nav = yield navigation_parser.optional()
    pinned = yield pin_parser
    return Part(term, pinned, nav)


@make_parser
def key_value_parser() -> Parser:
    key = yield preamble_prop_p
    yield equals_p
    value = yield quoted_string_p | true_p | false_p | float_p | integer_p | literal_p
    return key, value


@make_parser
def preamble_tags_parser() -> Parser:
    yield lparen_p
    key_values = yield key_value_parser.sep_by(comma_p)
    yield rparen_p
    return dict(key_values)


as_p = lexeme(string("as"))
aggregate_p = lexeme(string("aggregate"))
aggregate_func_p = reduce(lambda x, y: x | y, [lexeme(string(a)) for a in ["sum", "count", "min", "max", "avg"]])
match_p = lexeme(string("match"))


@make_parser
def aggregate_group_variable_parser() -> Parser:
    name = yield variable_p
    with_as = yield as_p.optional()
    as_name = None
    if with_as:
        as_name = yield literal_p
    return AggregateVariable(name, as_name)


math_op_p = reduce(lambda x, y: x | y, [lexeme(string(a)) for a in ["+", "-", "*", "/", "%"]])


@make_parser
def op_with_val_parser() -> Parser:
    op = yield math_op_p
    value = yield float_p | integer_p
    return op, value


@make_parser
def aggregate_group_function_parser() -> Parser:
    func = yield aggregate_func_p
    yield lparen_p
    term_or_int = yield variable_p | integer_p
    ops_list = yield op_with_val_parser.many()
    yield rparen_p
    with_as = yield as_p.optional()
    as_name = None
    if with_as:
        as_name = yield literal_p
    return AggregateFunction(func, term_or_int, ops_list, as_name)


@make_parser
def aggregate_parameter_parser() -> Parser:
    group_vars = yield (aggregate_group_variable_parser.sep_by(comma_p, min=1) << colon_p).optional()
    group_function_vars = yield aggregate_group_function_parser.sep_by(comma_p, min=1)
    return group_vars if group_vars else [], group_function_vars


@make_parser
def aggregate_parser() -> Parser:
    yield aggregate_p
    yield lparen_p
    group_vars, group_function_vars = yield aggregate_parameter_parser
    yield rparen_p
    return Aggregate(group_vars, group_function_vars)


@make_parser
def match_parser() -> Parser:
    yield match_p
    yield lparen_p.optional()
    yield rparen_p.optional()
    # a preamble of match() is the default query behaviour and only here for syntactic sugar
    return None


@make_parser
def preamble_parser() -> Parser:
    maybe_aggegate = yield (aggregate_parser | match_parser).optional()
    maybe_preamble = yield preamble_tags_parser.optional()
    preamble = maybe_preamble if maybe_preamble else dict()
    yield colon_p if maybe_aggegate or maybe_preamble else colon_p.optional()
    return maybe_aggegate, preamble


sort_order_p = string("asc") | string("desc")
sort_dp = string("sort")


@make_parser
def single_sort_arg_parser() -> Parser:
    name = yield variable_dp
    order = yield (space_dp >> sort_order_p).optional()
    return Sort(name, order if order else SortOrder.Asc)


@make_parser
def sort_parser() -> Parser:
    yield sort_dp
    yield space_dp
    attributes = yield single_sort_arg_parser.sep_by(comma_p, min=1)
    yield whitespace
    return attributes


limit_p = string("limit")
limit_parser = limit_p + space_dp >> integer_dp


@make_parser
def query_parser() -> Parser:
    maybe_aggregate, preamble = yield preamble_parser
    parts = yield part_parser.at_least(1)
    edge_type = preamble.get("edge_type", EdgeType.default)
    if edge_type not in EdgeType.allowed_edge_types:
        raise AttributeError(f"Given edge_type {edge_type} is not available. Use one of {EdgeType.allowed_edge_types}")
    adapted = [
        replace(part, navigation=replace(part.navigation, edge_type=edge_type))
        if part.navigation and not part.navigation.edge_type
        else part
        for part in parts
    ]
    sort = yield sort_parser.optional()
    limit = yield limit_parser.optional()
    return Query(adapted[::-1], preamble, maybe_aggregate, sort, limit)


def parse_query(query: str) -> Query:
    return query_parser.parse(query.strip())  # type: ignore
