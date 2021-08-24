import keeper_cli.logging
import sys
import pathlib
import requests
import json
from keeper_cli.args import get_arg_parser, ArgumentParser
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory


log = keeper_cli.logging.getLogger(__name__)


def main() -> None:
    arg_parser = get_arg_parser()
    add_args(arg_parser)
    arg_parser.parse_args()

    session = completer = None
    history_file = str(pathlib.Path.home() / ".keeper_history")
    history = FileHistory(history_file)
    session = PromptSession(history=history)
    evaluate_endpoint = f"{ArgumentParser.args.keepercore_uri}/cli/evaluate"
    execute_endpoint = f"{ArgumentParser.args.keepercore_uri}/cli/execute"

    while True:
        try:
            cli_input = session.prompt("> ", completer=completer)
            if cli_input == "":
                continue

            res = requests.post(evaluate_endpoint, data=cli_input)
            if res.status_code != 200:
                print(res.text, file=sys.stderr)
                continue

            res = requests.post(execute_endpoint, data=cli_input)
            if res.status_code != 200:
                print(res.text, file=sys.stderr)
                continue

            response = json.loads(res.text)
            for line in response:
                print(line)

        except KeyboardInterrupt:
            pass
        except EOFError:
            sys.exit(0)
        except (RuntimeError, ValueError) as e:
            log.error(e)
        except Exception:
            log.exception("Caught unhandled exception while processing CLI command")


def add_args(arg_parser: ArgumentParser) -> None:
    arg_parser.add_argument(
        "--keepercore-uri",
        help="Keepercore URI",
        default="http://localhost:8080",
        dest="keepercore_uri",
    )
    arg_parser.add_argument(
        "--keepercore-ws-uri",
        help="Keepercore Websocket URI",
        default="ws://localhost:8080",
        dest="keepercore_ws_uri",
    )


if __name__ == "__main__":
    main()
