import socket
import requests
import time
import cklib.logging as logging
from cklib.args import ArgumentParser, get_arg_parser
from cklib.event import add_args as event_add_args, Event, EventType
from cloudkeeper.web import WebServer, CloudkeeperWebApp
from cklib.graph import GraphContainer

logging.getLogger("cloudkeeper").setLevel(logging.DEBUG)


def test_web():
    arg_parser = get_arg_parser()
    WebServer.add_args(arg_parser)
    event_add_args(arg_parser)
    arg_parser.parse_args()

    gc = GraphContainer(cache_graph=False)
    # Find a free local port to reuse when we bind the web server.
    # This is so that multiple builds/tests can run in parallel
    # on the same CI agent.
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(("", 0))
    _, free_port = tcp.getsockname()
    ArgumentParser.args.web_port = free_port
    tcp.close()
    # todo: race between closing socket and reusing free port in WebServer

    web_server = WebServer(CloudkeeperWebApp(gc))
    web_server.daemon = True
    web_server.start()
    start_time = time.time()
    while not web_server.serving:
        if time.time() - start_time > 10:
            raise RuntimeError("timeout waiting for web server start")
        time.sleep(0.1)

    # We're statically using localhost in the endpoint url.
    # Other options would have been to set ArgumentParser.args.web_host
    # and then connect to that value. However we'd have to use an IP
    # address and then needed to decide if we use either
    # 127.0.0.1 or ::1. Which might fail on CI boxes without
    # IPv4 or IPv6 respectively. Instead we leave the default which
    # binds to all IPs and assume that localhost will resolve to
    # the appropriate v4 or v6 loopback address. A disadvantage
    # of this is that for a brief moment during the test we're
    # exposing the web server on all local IPs.
    endpoint = f"http://localhost:{ArgumentParser.args.web_port}"
    r = requests.get(f"{endpoint}/health")
    assert r.content == b"ok\r\n"
    web_server.shutdown(Event(EventType.SHUTDOWN))
