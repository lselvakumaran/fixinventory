from resoto_plugin_digitalocean import DigitalOceanCollectorPlugin
from resotolib.args import get_arg_parser


def test_args():
    arg_parser = get_arg_parser()
    DigitalOceanCollectorPlugin.add_args(arg_parser)
    arg_parser.parse_args()
    assert True
