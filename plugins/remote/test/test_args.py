from resotolib.args import get_arg_parser, ArgumentParser
from resoto_plugin_remote import RemotePlugin


def test_args():
    arg_parser = get_arg_parser()
    RemotePlugin.add_args(arg_parser)
    arg_parser.parse_args()
    assert len(ArgumentParser.args.remote_endpoint) == 0
