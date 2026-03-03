from argparse import ArgumentTypeError
from typing import Any, override
from core.app import get_builtin
from core.bases.logic_sc import LogicAddress, LogicServer, DataTypes


class BuiltinAddress(LogicAddress):
    @override
    def __str__(self) -> str:
        return 'ui thread'


class BuiltinServer(LogicServer):
    global BUILTIN_SERVER_ADDRESS

    @override
    def connect(self, address: LogicAddress | None = None) -> bool:
        if address is None:
            address = self.address
        if address is BUILTIN_SERVER_ADDRESS:
            return get_builtin()
        else:
            return False

    @override
    def is_connected(self) -> bool:
        return bool(BUILTIN_SERVER_ADDRESS)

    @override
    def close_connect(self) -> None:
        pass

    @override
    def send(self, data: Any, data_type: str = DataTypes.BYTES):
        ...


BUILTIN_SERVER_ADDRESS: BuiltinAddress | None = None


def get_builtin_server_address() -> BuiltinAddress:
    global BUILTIN_SERVER_ADDRESS
    if not get_builtin():
        raise ArgumentTypeError("IS_BUILTIN cannot be 'False'")
    if not BUILTIN_SERVER_ADDRESS is None:
        return BUILTIN_SERVER_ADDRESS
    else:
        BUILTIN_SERVER_ADDRESS = BuiltinAddress(None, -1)
        return BUILTIN_SERVER_ADDRESS
