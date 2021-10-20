import logging
import os
import sys
from datetime import timedelta

from aiohttp import web
from aiohttp.web_app import Application

from core.cli.cli import CLI
from core.cli.command import all_parts, aliases, CLIDependencies
from core.dependencies import db_access, setup_process, parse_args
from core.message_bus import MessageBus
from core.model.model_handler import ModelHandlerDB
from core.task.scheduler import Scheduler
from core.task.subscribers import SubscriptionHandler
from core.task.task_handler import TaskHandler
from core.web.api import Api
from core.worker_task_queue import WorkerTaskQueue

log = logging.getLogger(__name__)


def main() -> None:

    args = parse_args()
    setup_process(args)

    log.info("Starting up...")
    message_bus = MessageBus()
    db = db_access(args, message_bus)
    # wait here for an initial connection to the database before we continue
    db.wait_for_initial_connect(timedelta(seconds=60))
    scheduler = Scheduler()
    worker_task_queue = WorkerTaskQueue()
    model = ModelHandlerDB(db.get_model_db(), args.plantuml_server)
    cli_deps = CLIDependencies()
    cli = CLI(cli_deps, all_parts(cli_deps), dict(os.environ), aliases())

    subscriptions = SubscriptionHandler(db.subscribers_db, message_bus)
    task_handler = TaskHandler(db.running_task_db, db.job_db, message_bus, subscriptions, scheduler, cli, args)
    cli_deps.lookup = {
        "message_bus": message_bus,
        "db_access": db,
        "model_handler": model,
        "job_handler": task_handler,
        "worker_task_queue": worker_task_queue,
    }
    api = Api(db, model, subscriptions, task_handler, message_bus, worker_task_queue, cli, args)

    async def async_initializer() -> Application:
        await db.start()
        await subscriptions.start()
        # todo: how to use context managed objects with aiohttp?
        await task_handler.__aenter__()
        await scheduler.start()
        await worker_task_queue.start()
        log.info("Initialization done. Starting API.")
        return api.app

    web.run_app(async_initializer(), host=args.host, port=args.port)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Stopping Cloudkeeper graph core.")
        sys.exit(0)
    except Exception as ex:
        log.error(f"Error starting Cloudkeeper graph core: {ex}")
        sys.exit(1)
