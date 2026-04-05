import signal
import time
import os
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
    AssignmentDelPacket
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
    id: int | None = None


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


class AgendaXServer:
    _port = 2000
    _state = ServerState.INIT

    def __init__(self, create_socket: bool = True):
        from core.app import LOG
        self.LOG = LOG
        if create_socket:
            self.database = DatabaseHelper()
        self.settings = Settings()

        # 当 create_socket 为 True 时创建监听 socket，否则留空以便子类（如 RemoteServer）使用不同的行为
        self._socket = None
        if create_socket:
            self._socket = socket(AF_INET, SOCK_STREAM)
        # clients 列表在本类逻辑中可能被使用，始终保持存在
        self._clients: list[socket] = []

        # 线程池无论如何都初始化（RemoteServer 仍可以使用 run_later 调度任务）
        self._executor = ThreadPoolExecutor(
            max_workers=self.settings.get("max_workers", 10),
            thread_name_prefix="AgendaXWorker"
        )

        # 仅在创建本地 socket 时注册 OS 信号处理（RemoteServer 作为客户端不需要）
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

        # 如果没有 socket（例如 RemoteServer 会覆写或用不同逻辑），尝试调用 handle_connection，
        # 子类可覆写 handle_connection 做适当的行为
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

        # 关闭 socket（若存在），忽略异常
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
    def _signal_handler(self, signum, frame):
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
                    self.LOG.info(f"Received HelloPacket from {addr}: {packet.get_value()}")
                elif isinstance(packet, AssignmentPacket):
                    assignment = packet.get_value()
                    self.update_assignment(assignment)
                elif isinstance(packet, AssignmentDelPacket):
                    subject_id = packet.get_value()
                    self.del_assignment_by_subject(subject_id)
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

    def __str__(self):
        return f"<LocalServer:{self._port}>"

    def send_shutdown_message(self):
        for client in self._clients:
            try:
                self.send_packet(client, ShutdownPacket.create())
            except Exception:
                pass

    def send_packet(self, client: socket, packet: Packet):
        try:
            client.send(HeadPacket.create(packet).to_bytes())
            client.send(packet.to_bytes())
        except Exception as e:
            # 安全获取 peer 信息，避免在非套接字或已关闭套接字上调用 getpeername 导致 OSError
            try:
                peer = client.getpeername()
            except Exception:
                peer = "<unknown-socket>"
            self.LOG.error(f"Failed to send packet to {peer}: {e}", exc_info=True)

    def wait_for_next_packet(self, _socket: socket) -> Optional[Packet]:
        # 先做基本有效性检查（_socket 可能在子类中为 None 或被关闭）
        if _socket is None:
            return None
        if not hasattr(_socket, "recv") or not callable(getattr(_socket, "recv")):
            return None

        try:
            head_data = _socket.recv(HeadPacket.length())
            # socket.recv 返回空 bytes 表示对端已关闭连接
            if not head_data:
                raise RuntimeError("Connection closed by peer")

            packet = get_packet(head_data)
            _body_length: int = 0

            if isinstance(packet, HeadPacket):
                _body_length = packet.get_value()
            else:
                self.LOG.error(f"Expected HeadPacket but got {type(packet).__name__}")
                return None

            # 保证读取到完整 body（简单实现：循环读取直到长度满足或连接断开）
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
            # 避免在此处直接调用 _socket.getpeername()，可能导致 WinError 10038
            try:
                peer = _socket.getpeername()
            except Exception:
                peer = "<unknown-socket>"
            self.LOG.error(f"Error receiving packet from {peer}: {e}", exc_info=True)
            return None

    def get_assignment_by_id(self, subject_id: str):
        return self.database.get_by_subject(subject_id, table="AssignmentTable")

    def del_assignment_by_id(self, subject_id: int):
        with Session(self.database.engine) as session:
            stmt = delete(AssignmentTable).where(AssignmentTable.id == subject_id)
            session.exec(stmt)
            session.commit()

    def update_assignment(self, assignment: Assignment):
        with Session(self.database.engine) as session:
            if assignment.id is None:
                raise ValueError("Assignment must have an id for update")

            stmt = (
                select(AssignmentTable)
                .where(AssignmentTable.id == assignment.id)
            )
            existing = session.exec(stmt).one_or_none()

            if not existing:
                # 添加新纪录
                self.database.add(assignment)
                return

            existing.subject = assignment.subject
            existing.data_type = assignment.data_type
            existing.data = assignment.data
            existing.start_time = assignment.start_time
            existing.finish_time = assignment.finish_time
            existing.finish_time_type = assignment.finish_time_type

            session.add(existing)
            session.commit()
