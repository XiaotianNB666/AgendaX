from abc import ABC, abstractmethod
from enum import Enum, unique
from typing import Callable, Any, TypeVar, Iterable, Optional, Set, Union

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


# Helper: normalize various receiver inputs to a set of Receiver enum members
def _to_receiver_set(value: Optional[Union[Receiver, ReceiverGroup, Iterable[Union[Receiver, ReceiverGroup]]]]) -> Optional[Set[Receiver]]:
    if value is None:
        return None
    # Single Receiver
    if isinstance(value, Receiver):
        return {value}
    # Single ReceiverGroup -> its value is a list of Receiver
    if isinstance(value, ReceiverGroup):
        return set(value.value)
    # Iterable of Receiver/ReceiverGroup
    if isinstance(value, Iterable):
        s: Set[Receiver] = set()
        for item in value:
            if isinstance(item, Receiver):
                s.add(item)
            elif isinstance(item, ReceiverGroup):
                s.update(item.value)
            else:
                # ignore unknown items
                continue
        return s
    return None


class Event(ABC):
    # 子类会自动获取基于类名的 id，子类也可以显式覆盖
    id: str | None = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 只有在子类未显式设置 id 时，自动根据类名生成 id
        if not getattr(cls, "id", None):
            cls.id = snake(cls.__name__)

    def __init__(self):
        ...

    @abstractmethod
    def get_value(self) -> Any:
        return None


class EventHandler:
    def __init__(self, func: Callable, receiver: Optional[Union[Receiver, ReceiverGroup, Iterable[Union[Receiver, ReceiverGroup]]]] = None):
        # handler 的接收者总是以 Receiver 的集合形式保存，默认允许所有人
        self.receiver_raw = receiver if receiver is not None else ReceiverGroup.ALL
        self.receivers: Set[Receiver] = _to_receiver_set(self.receiver_raw) or set()
        self.func = func

    def execute(self, event: Event):
        try:
            self.func(event)
        except Exception:
            # 不在此文件中引入日志，保持灵活；上层可捕获或日志化
            raise


_EVENTS: dict[str, list[EventHandler]] = {}


def fire_event(event: Event, receiver_group: Optional[Union[Receiver, ReceiverGroup, Iterable[Union[Receiver, ReceiverGroup]]]] = None):
    """
    dispatch event to handlers whose receivers intersect with receiver_group.
    If receiver_group is None => dispatch to all registered handlers for this event id.
    """
    global _EVENTS
    handlers = _EVENTS.get(event.id, [])
    target_set = _to_receiver_set(receiver_group)
    for handler in handlers:
        # 如果没有指定 target_set，则广播；否则当 handler.receivers 与 target_set 有交集时执行
        if (target_set is None) or (handler.receivers & target_set):
            handler.execute(event)


def fire_event_async(event: Event, receiver_group: Optional[Union[Receiver, ReceiverGroup, Iterable[Union[Receiver, ReceiverGroup]]]] = None):
    Task(f"fire_event${event.id}", lambda: fire_event(event, receiver_group), Task.MIN).execute()


_T = TypeVar('_T', bound=Event)
def register_event_handler(event: type[_T], func: Callable[[_T], Any], receiver: Optional[Union[Receiver, ReceiverGroup, Iterable[Union[Receiver, ReceiverGroup]]]] = None):
    """
    注册处理器。event 参数为 Event 子类（类型），func 接收该事件实例（或子类型）。
    receiver 可以传 Receiver、ReceiverGroup 或可迭代的上述元素集合。默认为 ReceiverGroup.ALL。
    """
    global _EVENTS
    handler = EventHandler(func, receiver)
    _EVENTS.setdefault(event.id, []).append(handler)


class SettingsLoadedEvent(Event):
    def get_value(self) -> dict:
        return self.settings

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings


class ExitEvent(Event):
    def get_value(self) -> None:
        return None
