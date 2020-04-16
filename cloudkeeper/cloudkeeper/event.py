from cloudkeeper.utils import RWLock
from cloudkeeper.args import ArgumentParser
from collections import defaultdict
from threading import Thread, Lock
from typing import Callable
from enum import Enum
import os
import time
import logging

log = logging.getLogger(__name__)


class EventType(Enum):
    """Defines Event Types

    Event().data definitions for EventType:
    STARTUP: None
    SHUTDOWN: {'reason': 'reason for shutdown', 'emergency': True/False}
    START_COLLECT: None
    COLLECT_BEGIN: cloudkeeper.graph.Graph
    COLLECT_FINISH: cloudkeeper.graph.Graph
    CLEANUP_BEGIN: cloudkeeper.graph.Graph
    CLEANUP_FINISH: cloudkeeper.graph.Graph
    PROCESS_BEGIN: cloudkeeper.graph.Graph
    PROCESS_FINISH: cloudkeeper.graph.Graph
    GENERATE_METRICS: cloudkeeper.graph.Graph
    """
    STARTUP = 'startup'
    SHUTDOWN = 'shutdown'
    START_COLLECT = 'start_collect'
    COLLECT_BEGIN = 'collect_begin'
    COLLECT_FINISH = 'collect_finish'
    CLEANUP_BEGIN = 'cleanup_begin'
    CLEANUP_FINISH = 'cleanup_finish'
    PROCESS_BEGIN = 'process_begin'
    PROCESS_FINISH = 'process_finish'
    GENERATE_METRICS = 'generate_metrics'


class Event:
    """An Event
    """
    def __init__(self, event_type: EventType, data=None) -> None:
        self.event_type = event_type
        self.data = data


_events = defaultdict(dict)
_events_lock = RWLock()


def event_listener_registered(event_type: EventType, listener: Callable) -> bool:
    """Return whether listener is registered to event
    """
    return event_type in _events.keys() and listener in _events[event_type].keys()


def dispatch_event(event: Event, blocking: bool = False) -> None:
    """Dispatch an Event
    """
    waiting_str = '' if blocking else 'not '
    log.debug(f'Dispatching event {event.event_type} and {waiting_str}waiting for listeners to return')

    if event.event_type not in _events.keys():
        return

    with _events_lock.read_access:
        # Event listeners might unregister themselves during event dispatch
        # so we will work on a shallow copy while processing the current event.
        listeners = dict(_events[event.event_type])

    threads = {}
    for listener, listener_data in listeners.items():
        try:
            if listener_data['one-shot'] and not listener_data['lock'].acquire(blocking=False):
                log.error(f"Not calling one-shot event listener {listener} of type {type(listener)} - can't acquire lock")
                continue

            log.debug(f"Calling event listener {listener} of type {type(listener)} (blocking: {listener_data['blocking']})")
            thread_name = f"{event.event_type.name.lower()}_event-{getattr(listener, '__name__', 'anonymous')}"
            t = Thread(target=listener, args=[event], name=thread_name)
            if blocking or listener_data['blocking']:
                threads[listener] = t
            t.start()
        except Exception:
            log.exception('Caught unhandled event callback exception')
        finally:
            if listener_data['one-shot']:
                log.debug(f'One-shot specified for event {event.event_type.name} listener {listener} - removing event listener')
                remove_event_listener(event.event_type, listener)
                listener_data['lock'].release()

    start_time = time.time()
    for listener, thread in threads.items():
        timeout = start_time + listeners[listener]['timeout'] - time.time()
        if timeout < 1:
            timeout = 1
        log.debug(f'Waiting up to {timeout:.2f}s for event listener {thread.name} to finish')
        thread.join(timeout)
        log.debug(f'Event listener {thread.name} finished (timeout: {thread.is_alive()})')


def add_event_listener(event_type: EventType, listener: Callable, blocking: bool = False, timeout: int = None, one_shot: bool = False) -> bool:
    """Add an Event Listener
    """
    if not callable(listener):
        log.error(f'Error registering {listener} of type {type(listener)} with event {event_type.name}')
        return False

    if timeout is None:
        timeout = ArgumentParser.args.event_timeout

    log.debug(f'Registering {listener} with event {event_type}')
    with _events_lock.write_access:
        if not event_listener_registered(event_type, listener):
            _events[event_type][listener] = {'blocking': blocking, 'timeout': timeout, 'one-shot': one_shot, 'lock': Lock()}
            return True
        return False


def remove_event_listener(event_type: EventType, listener: Callable) -> bool:
    """Remove an Event Listener
    """
    with _events_lock.write_access:
        if event_listener_registered(event_type, listener):
            log.debug(f'Removing {listener} from event {event_type}')
            del _events[event_type][listener]
            if len(_events[event_type]) == 0:
                del _events[event_type]
            return True
        return False


def add_args(arg_parser: ArgumentParser) -> None:
    arg_parser.add_argument('--event-timeout', help='Event Listener Timeout in seconds (default 900)',
                            default=int(os.environ.get('CLOUDKEEPER_EVENT_TIMEOUT', 900)), dest='event_timeout',
                            type=int)
