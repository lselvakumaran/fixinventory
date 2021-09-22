from datetime import datetime
from pathlib import Path
from cklib.baseplugin import BasePlugin
from cklib.graph import graph2pickle
from cklib.args import ArgumentParser
from cklib.event import Event, EventType, add_event_listener
from cklib.logging import log


class BackupPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.name = "backup"
        if ArgumentParser.args.backup_to:
            add_event_listener(EventType.COLLECT_FINISH, BackupPlugin.backup_graph)

    def go(self):
        pass

    @staticmethod
    def backup_graph(event: Event):
        graph = event.data
        backup = graph2pickle(graph)
        backup_file = f"{'graph'}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}.bak"
        backup_path = Path(ArgumentParser.args.backup_to) / backup_file
        log.info(f"Graph Backup to {backup_path}")
        with open(backup_path, "wb") as f:
            f.write(backup)

    @staticmethod
    def add_args(arg_parser: ArgumentParser) -> None:
        arg_parser.add_argument(
            "--backup-to", help="Backup Destination", default=None, dest="backup_to"
        )
