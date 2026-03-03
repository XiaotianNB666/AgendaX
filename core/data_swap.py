from core.bases.logic_sc import LogicClient, LogicServer

FROM_CLIENTS: dict[LogicClient, list[tuple[bytes, str]]] = {}
FROM_SERVER: list[tuple[bytes, str]] = []

CURRENT_SERVER: LogicServer | None = None


def set_current_server(cs: LogicServer) -> None:
    global CURRENT_SERVER
    CURRENT_SERVER = cs
