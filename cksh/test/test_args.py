from cklib.args import ArgumentParser
from cksh.__main__ import add_args


def test_args():
    arg_parser = ArgumentParser(
        description="Cloudkeeper Shell", env_args_prefix="CKSH_"
    )
    add_args(arg_parser)
    arg_parser.parse_args()
    assert ArgumentParser.args.ckcore_uri == "http://localhost:8900"
