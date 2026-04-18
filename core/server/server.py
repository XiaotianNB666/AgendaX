import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum, auto
from socket import socket, AF_INET, SOCK_STREAM
from typing import Callable, Sequence, Optional

from sqlalchemy import delete
from sqlmodel import create_engine, Session, select, SQLModel

from core.db.models import AssignmentTable, AssignmentRecord, ExerciseSubjectTable
from core.events import register_event_handler, ExitEvent, fire_event, Event
from core.server.packets import Packet, ShutdownPacket, HelloPacket, HeadPacket, get_packet, AssignmentPacket, \
    AssignmentDelPacket, ResourceResponsePacket, ResourceRequestPacket, MessagePacket
from core.settings import Settings
from core.utils.path_utils import get_work_dir

"""
表结构
AssignmentTable(id, subject, data_type, data, start_time, finish_time, finish_time_type)
AssignmentRecord(id, subject, data_type, data, start_time, finish_time, finish_time_type)
"""


# =========================
# Assignment DTO
# =========================
@dataclass
class Assignment:
    subject: str
    data_type: str
    data: str
    start_time: float = field(default_factory=time.time)
    finish_time: float | None = None
    finish_time_type: str = ""
    id: Optional[int] = None

    @classmethod
    def create(cls, subject_id: str, data_type: str, data: str, start_time: float, finish_time: float,
               finish_time_type: str):
        return cls(subject_id, data_type, data, start_time, finish_time, finish_time_type)

    def __repr__(self) -> str:
        return (
            f"Assignment("
            f"id={self.id}, "
            f"subject={self.subject!r}, "
            f"data_type={self.data_type!r}, "
            f"start_time={self.start_time}, "
            f"finish_time={self.finish_time}, "
            f"finish_time_type={self.finish_time_type!r})"
        )



# =========================
# Database Helper (SQLModel)
# =========================
class DatabaseHelper:
    def __init__(self):
        db_path = os.path.join(get_work_dir('.app'), '.data')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False
        )

        SQLModel.metadata.create_all(self.engine)

        from core.app import LOG
        LOG.info(f"Database initialized at {db_path}")

    def add(self, obj: Assignment, table: str = "AssignmentTable") -> int:
        with Session(self.engine) as session:
            model = {
                "AssignmentTable": AssignmentTable,
                "AssignmentRecord": AssignmentRecord,
            }.get(table)

            if not model:
                raise ValueError(f"Invalid table name: {table}")

            instance = model(
                subject=obj.subject,
                data_type=obj.data_type,
                data=obj.data,
                start_time=obj.start_time,
                finish_time=obj.finish_time,
                finish_time_type=obj.finish_time_type,
            )

            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance.id

    def get_by_subject(
            self,
            subject: str,
            table: str = "AssignmentTable"
    ) -> list[Assignment]:
        with Session(self.engine) as session:
            model = {
                "AssignmentTable": AssignmentTable,
                "AssignmentRecord": AssignmentRecord,
            }.get(table)

            if not model:
                raise ValueError(f"Invalid table name: {table}")

            stmt = select(model).where(model.subject == subject)
            rows = session.exec(stmt).all()

            return [
                Assignment(
                    id=row.id,
                    subject=row.subject,
                    data_type=row.data_type,
                    data=row.data,
                    start_time=row.start_time,
                    finish_time=row.finish_time,
                    finish_time_type=row.finish_time_type,
                )
                for row in rows
            ]

    def bind_exercise_subject(self, exercise: str, subject: str):
        with Session(self.engine) as session:
            obj = ExerciseSubjectTable(exercise=exercise, subject=subject)
            session.merge(obj)
            session.commit()

    def unbind_exercise_subject(self, exercise: str, subject: str):
        with Session(self.engine) as session:
            stmt = (
                delete(ExerciseSubjectTable)
                .where(
                    ExerciseSubjectTable.exercise == exercise,
                    ExerciseSubjectTable.subject == subject
                )
            )
            session.exec(stmt)
            session.commit()

    def get_subjects_by_exercise(self, exercise: str) -> Sequence[str]:
        with Session(self.engine) as session:
            stmt = select(ExerciseSubjectTable.subject).where(
                ExerciseSubjectTable.exercise == exercise
            )
            return session.exec(stmt).all()

    def get_exercises_by_subject(self, subject: str) -> Sequence[str]:
        with Session(self.engine) as session:
            stmt = select(ExerciseSubjectTable.exercise).where(
                ExerciseSubjectTable.subject == subject
            )
            return session.exec(stmt).all()

    def get_assignment_by_ass_id(self, _id: int):
        with Session(self.engine) as session:
            model = AssignmentTable

            stmt = select(model).where(model.id == _id)
            rows = session.exec(stmt).all()

            return [
                Assignment(
                    id=row.id,
                    subject=row.subject,
                    data_type=row.data_type,
                    data=row.data,
                    start_time=row.start_time,
                    finish_time=row.finish_time,
                    finish_time_type=row.finish_time_type,
                )
                for row in rows
            ]


class ServerStartedEvent(Event):
    def __init__(self, server):
        super().__init__()
        self._server = server

    def get_value(self):
        return self._server


# =========================
# Server Lifecycle
# =========================
class ServerState(Enum):
    INIT = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()


def get_objects_path(identity: str) -> str:
    return os.path.join(get_work_dir('.app'), '_objects', identity)


def get_res_data(identity: str) -> bytes:
    _data_path = os.path.join(get_work_dir('.app'), '_objects')
    os.makedirs(_data_path, exist_ok=True)
    try:
        with open(os.path.join(_data_path, identity), 'rb') as f:
            return f.read()
    except (FileNotFoundError, IOError):
        return b""


def _strict_isinstance(obj, cls):
    return type(obj) is cls


class AgendaXServer:
    _port = 2000
    _state = ServerState.INIT

    def __init__(self, create_socket: bool = True):
        from core.app import LOG
        self.LOG = LOG
        if create_socket:
            self.database = DatabaseHelper()
        self.settings = Settings()

        self._socket = None
        if create_socket:
            self._socket = socket(AF_INET, SOCK_STREAM)
        self._clients: list[socket] = []

        self._executor = ThreadPoolExecutor(
            max_workers=self.settings.get("max_workers", 10),
            thread_name_prefix="AgendaXWorker"
        )

        if create_socket:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

        register_event_handler(ExitEvent, lambda e: self.shutdown())

        fire_event(ServerStartedEvent(self))

    # =========================
    # State
    # =========================
    @property
    def running(self) -> bool:
        return self._state == ServerState.RUNNING

    # =========================
    # Lifecycle
    # =========================
    def start(self):
        if self._state != ServerState.INIT:
            raise RuntimeError("Server already started")

        self.LOG.info("Starting AgendaXServer...")
        self._state = ServerState.RUNNING

        try:
            self.handle_connection()
        except Exception as e:
            self.LOG.error(f"Error in handle_connection: {e}", exc_info=True)
            self.shutdown()

    def shutdown(self, quit_app: bool = True):
        from core.app import app_quit
        if self._state != ServerState.RUNNING:
            return

        self.LOG.info("Stopping AgendaXServer...")
        self._state = ServerState.STOPPING

        # 先停止线程池
        try:
            self._executor.shutdown(wait=False)
        except Exception as e:
            self.LOG.debug(f"Executor shutdown error: {e}", exc_info=True)

        # 关闭 socket
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            except Exception:
                self.LOG.debug("Exception while closing socket", exc_info=True)

        self._state = ServerState.STOPPED
        self.LOG.info("AgendaXServer stopped.")
        if quit_app:
            app_quit()

    # =========================
    # Signal
    # =========================
    def _signal_handler(self, signum):
        self.LOG.warning(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()

    # =========================
    # Task Scheduler
    # =========================
    def run_later(self, func: Callable):
        if not self.running:
            self.LOG.warning("Ignored run_later call while server not running")
            return

        try:
            self._executor.submit(func)
        except RuntimeError as e:
            self.LOG.error(f"Failed to schedule task: {e}")

    # =========================
    # Socket Accept
    # =========================
    def handle_connection(self):
        # 如果没有创建 socket，默认行为是记录并返回，子类（如 RemoteServer）可以覆写此方法
        if self._socket is None:
            self.LOG.debug("No server socket created; handle_connection skipped.")
            return

        self._socket.bind(("0.0.0.0", self._port))
        self._socket.listen(5)

        # 防止 Windows 10038
        self._socket.settimeout(1.0)

        self.LOG.info(f"Listening on port: {self._port}")

        while self.running:
            try:
                client_socket, addr = self._socket.accept()
                self.LOG.info(f"Accepted connection from {addr}")

                self.run_later(
                    lambda cs=client_socket, ca=addr:
                    self._handle_client(cs, ca)
                )

            except TimeoutError:
                continue

            except OSError as e:
                if self.running:
                    self.LOG.error(f"Socket error: {e}")
                break

    # =========================
    # Client Handler
    # =========================
    def _handle_client(self, client_socket: socket, addr: tuple):
        self._clients.append(client_socket)

        try:
            from core.app import APP, version
            self.send_packet(client_socket, HelloPacket.create())

            while self.running:
                packet = self.wait_for_next_packet(client_socket)
                if packet is None:
                    continue
                if isinstance(packet, HelloPacket):
                    _version, _display_name = packet.get_value()
                    self.LOG.info(f"Received HelloPacket from {addr}[{_version}]. Name: {_display_name}")
                elif isinstance(packet, AssignmentPacket):
                    assignment = packet.get_value()
                    self.update_assignment(assignment)
                elif isinstance(packet, AssignmentDelPacket):
                    subject_id = packet.get_value()
                    self.del_assignment_by_id(subject_id)
                elif isinstance(packet, ResourceResponsePacket):
                    data = packet.get_value()
                    file_name = data[1].__hash__() if data[0] is None else data[0]
                    self.save_resource(str(file_name), data[1])
                elif isinstance(packet, ResourceRequestPacket):
                    identity = packet.get_value()
                    file = get_res_data(identity)
                    self.send_packet(client_socket, ResourceResponsePacket.create(file))
                elif _strict_isinstance(packet, MessagePacket):
                    self.LOG.info(f"Message from {addr}: {packet.get_value()}")

        except RuntimeError:
            pass
        finally:
            try:
                client_socket.close()
            except Exception:
                pass
            if client_socket in self._clients:
                self._clients.remove(client_socket)
            self.LOG.info(f"Client disconnected: {addr}")

    def save_resource(self, file_name, data: bytes):
        _data_path = os.path.join(get_work_dir('.app'), '_objects')
        os.makedirs(_data_path, exist_ok=True)

        try:
            with open(os.path.join(_data_path, str(file_name)), 'wb') as f:
                f.write(data)
        except Exception as e:
            self.LOG.error(f"Failed to save resource: {e}", exc_info=True)

    def __str__(self):
        return f"<LocalServer:{self._port}>"

    def send_shutdown_message(self):
        for client in self._clients:
            try:
                self.send_packet(client, ShutdownPacket.create())
            except Exception:
                pass

    def send_packet(self, client: Optional[socket], packet: Packet):
        if not client:
            self.LOG.warning("Attempted to send packet to None client")
            return
        try:
            client.send(HeadPacket.create(packet).to_bytes())
            client.send(packet.to_bytes())
        except Exception as e:
            try:
                peer = client.getpeername()
            except Exception:
                peer = "<unknown-socket>"
            self.LOG.error(f"Failed to send packet to {peer}: {e}", exc_info=True)

    def wait_for_next_packet(self, _socket: socket) -> Optional[Packet]:
        if _socket is None:
            return None
        if not hasattr(_socket, "recv") or not callable(getattr(_socket, "recv")):
            return None

        try:
            head_data = _socket.recv(HeadPacket.length())
            if not head_data:
                raise RuntimeError("Connection closed by peer")

            packet = get_packet(head_data)
            _body_length: int = 0

            if isinstance(packet, HeadPacket):
                _body_length = packet.get_value()
            else:
                self.LOG.error(f"Expected HeadPacket but got {type(packet).__name__}")
                return None

            body_chunks = []
            remaining = _body_length
            while remaining > 0:
                chunk = _socket.recv(remaining)
                if not chunk:
                    raise RuntimeError("Connection closed while receiving body")
                body_chunks.append(chunk)
                remaining -= len(chunk)
            body_data = b"".join(body_chunks)
            return get_packet(body_data)
        except (ConnectionResetError, ConnectionAbortedError, RuntimeError) as e:
            # 连接已关闭/重置，抛出以便上层清理
            self.LOG.warning(f"Connection reset/closed: {e}")
            raise RuntimeError(f"Connection reset/closed: {e}")
        except Exception as e:
            try:
                peer = _socket.getpeername()
            except Exception:
                peer = "<unknown-socket>"
            self.LOG.error(f"Error receiving packet from {peer}: {e}", exc_info=True)
            return None

    def get_assignment_by_id(self, subject_id: str):
        return self.database.get_by_subject(subject_id, table="AssignmentTable")

    def _del_assignment_by_id(self, subject_id: int):
        with Session(self.database.engine) as session:
            stmt = delete(AssignmentTable).where(AssignmentTable.id == subject_id)
            session.exec(stmt)
            session.commit()

    def del_assignment(self, ass: Assignment):
        if ass.data_type.startswith('file:'):
            try:
                os.remove(get_objects_path(ass.data))
            except FileNotFoundError:
                pass
        self._del_assignment_by_id(ass.id)

    def update_assignment(self, assignment: Assignment) -> Optional[int]:
        try:
            with Session(self.database.engine) as session:
                if assignment.id is None:
                    return self.database.add(assignment)
                stmt = (
                    select(AssignmentTable)
                    .where(AssignmentTable.id == assignment.id)
                )
                existing = session.exec(stmt).one_or_none()
                if not existing:
                    return self.database.add(assignment)

                existing.subject = assignment.subject
                existing.data_type = assignment.data_type
                existing.data = assignment.data
                existing.start_time = assignment.start_time
                existing.finish_time = assignment.finish_time
                existing.finish_time_type = assignment.finish_time_type

                session.add(existing)
                session.commit()

                return assignment.id
        except Exception as e:
            self.LOG.error(f"Failed to update assignment: {e}", exc_info=True)

    @property
    def is_local(self) -> bool:
        return True

    def del_assignment_by_id(self, id):
        try:
            for it in self.database.get_assignment_by_ass_id(id):
                self.del_assignment(it)
        except:
            import traceback
            traceback.print_exc()
