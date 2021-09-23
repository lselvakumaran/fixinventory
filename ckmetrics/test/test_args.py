from cklib.args import get_arg_parser, ArgumentParser
from ckmetrics.__main__ import add_args


def test_args():
    arg_parser = get_arg_parser()
    add_args(arg_parser)
    arg_parser.parse_args()
    assert ArgumentParser.args.web_port == 9955
