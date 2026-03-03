from abc import ABC, abstractmethod
from typing import Any, Final, Callable

from core.bases.resource_release import ResourceReleasable


class DataTypes:
    STR: Final[str] = 's'
    BYTES: Final[str] = 'b'
    INT: Final[str] = 'i'
    FLOAT: Final[str] = 'f'
    DICT: Final[str] = 'd'
    LIST: Final[str] = 'L'
    NONE: Final[str] = ''
    OBJECT: Final[str] = 'o'  # only builtin supported


class LogicAddress(ABC):
    address: Any
    port: int

    def __init__(self, address, port: int) -> None:
        self.address = address
        self.port = port

    @abstractmethod
    def __str__(self) -> str:
        ...

    def value(self) -> tuple[Any, int]:
        return self.address, self.port


class LogicSC(ResourceReleasable):
    connection: Any = None
    address: Final[LogicAddress]
    receive_handler: Callable[[Any, str], None]

    def __init__(self, address: LogicAddress) -> None:
        self.register_release()
        if not isinstance(address, LogicAddress):
            from argparse import ArgumentTypeError
            raise ArgumentTypeError(f'need type LogicAddress but {type(address)}')
        self.address = address
        if not self.connect(address):
            raise RuntimeError(f'cannot connect to [{str(address)}]')

    @abstractmethod
    def connect(self, address: LogicAddress | None = None) -> bool:
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        ...

    @abstractmethod
    def close_connect(self) -> None:
        ...

    @abstractmethod
    def send(self, data: Any, data_type: str = DataTypes.BYTES):
        ...

    def release_resource(self):
        self.close_connect()

    def send_string_message(self, message: str):
        self.send(message, DataTypes.STR)

    def register_receive_handler(self, handler: Callable[[Any, str], None]):
        self.receive_handler = handler


class LogicClient(LogicSC):
    ...


class LogicServer(LogicSC):
    ...
