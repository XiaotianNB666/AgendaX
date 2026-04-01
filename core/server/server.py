import signal
import sys
import time
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum, auto
from socket import socket, AF_INET, SOCK_STREAM
from typing import Callable, Sequence

from sqlalchemy import delete
from sqlmodel import create_engine, Session, select, SQLModel

from core.db.models import AssignmentTable, AssignmentRecord, ExerciseSubjectTable
from core.events import register_event_handler, ExitEvent, fire_event, Event
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

    def __init__(self):
        from core.app import LOG
        self.LOG = LOG

        self.database = DatabaseHelper()
        self.settings = Settings()

        self._socket = socket(AF_INET, SOCK_STREAM)
        self._clients: list[socket] = []

        self._executor = ThreadPoolExecutor(
            max_workers=self.settings.get("max_workers", 10),
            thread_name_prefix="AgendaXWorker"
        )

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        register_event_handler(ExitEvent, lambda e:self.shutdown())
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
        self.handle_connection()

    def shutdown(self):
        if self._state != ServerState.RUNNING:
            return

        self.LOG.info("Stopping AgendaXServer...")
        self._state = ServerState.STOPPING

        self._executor.shutdown(wait=True)

        try:
            self._socket.close()
        except OSError:
            pass

        self._state = ServerState.STOPPED
        self.LOG.info("AgendaXServer stopped.")

    # =========================
    # Signal
    # =========================
    def _signal_handler(self, signum, frame):
        self.LOG.warning(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()
        sys.exit(0)

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
            client_socket.send(
                f"{APP.name}[{version()}]".encode("utf-8")
            )

            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break

        finally:
            client_socket.close()
            self._clients.remove(client_socket)
            self.LOG.info(f"Client disconnected: {addr}")