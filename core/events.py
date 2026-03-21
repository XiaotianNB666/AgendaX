from abc import ABC, abstractmethod
from enum import Enum, unique
from typing import Callable, Any

from core.utils.app_thread import Task
from core.utils.string_utils import snake


@unique
class Receiver(Enum):
    UI = 'UI'
    SETTINGS = 'SETTINGS'
    EVENTS = 'EVENTS'
    SERVER_NETWORK = 'SERVER_NETWORK'
    CLIENT_NETWORK = 'CLIENT_NETWORK'
    SERVER_THREAD = 'SERVER_THREAD'
    CLIENT_THREAD = 'CLIENT_THREAD'
    OTHER = None


@unique
class ReceiverGroup(Enum):
    SERVER = [Receiver.SETTINGS, Receiver.EVENTS, Receiver.SERVER_NETWORK, Receiver.SERVER_THREAD]
    CLIENT = [Receiver.SETTINGS, Receiver.EVENTS, Receiver.CLIENT_NETWORK, Receiver.CLIENT_THREAD]
    ALL = [
        Receiver.SETTINGS,
        Receiver.EVENTS,
        Receiver.SERVER_NETWORK,
        Receiver.SERVER_THREAD,
        Receiver.CLIENT_NETWORK,
        Receiver.CLIENT_THREAD,
        Receiver.OTHER
    ]


class Event(ABC):
    id: str = snake(__name__)

    def __init__(self):
        ...

    @abstractmethod
    def get_value(self) -> Any:
        return None


class EventHandler:
    def __init__(self, func: Callable, receiver=None):
        self.receiver = receiver if receiver is not None else ReceiverGroup.ALL
        self.func = func

    def execute(self, event: Event):
        self.func(event)


_EVENTS: dict[str, list[EventHandler]] = {}


def fire_event(event, receiver_group=None):
    global _EVENTS
    for handler in _EVENTS.get(event.id, []):
        if (receiver_group is None) or (handler.receiver in receiver_group):
            handler.execute(event)


def fire_event_async(event, receiver_group=None):
    Task(f"fire_event${event.id}", lambda: fire_event(event, receiver_group), Task.MIN).execute()


def register_event_handler(event: type[Event], func: Callable[[Event], Any], receiver=None):
    global _EVENTS
    if event.id in _EVENTS:
        _EVENTS[event.id].append(EventHandler(func, receiver))
    else:
        _EVENTS[event.id] = [EventHandler(func, receiver)]


class SettingsLoadedEvent(Event):
    def get_value(self) -> dict:
        return self.settings

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings


class ExitEvent(Event):
    def get_value(self) -> None:
        return None
