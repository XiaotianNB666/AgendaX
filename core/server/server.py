import sqlite3
import os
import threading
import time
from dataclasses import dataclass, field

from core.app import LOG
from core.settings import Settings
from core.utils.app_thread import Task
from core.utils.path_utils import get_work_dir

"""
表结构
AssignmentTable(id, subject, data_type, data, start_time, finish_time, finish_time_type)
AssignmentRecord(id, subject, data_type, data, start_time, finish_time, finish_time_type)
"""


@dataclass
class Assignment:
    subject: str
    data_type: str
    data: str
    start_time: float = field(default_factory=time.time)
    finish_time: float | None = None
    finish_time_type: str = ""
    id: int | None = None


class DatabaseHelper:
    def __init__(self):
        db_path = os.path.join(get_work_dir('.app'), '.data')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        if not os.path.exists(db_path):
            LOG.info(f"Creating database: {db_path}")
        self._init_tables()

    # =========================
    # 表初始化
    # =========================
    def _init_tables(self):
        LOG.info("Initializing database tables")

        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS AssignmentTable
                            (
                                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                                subject          TEXT NOT NULL,
                                data_type        TEXT NOT NULL,
                                data             TEXT,
                                start_time       REAL,
                                finish_time      REAL,
                                finish_time_type TEXT
                            )
                            """)

        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS AssignmentRecord
                            (
                                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                                subject          TEXT NOT NULL,
                                data_type        TEXT NOT NULL,
                                data             TEXT,
                                start_time       REAL,
                                finish_time      REAL,
                                finish_time_type TEXT
                            )
                            """)

        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS ExerciseSubjectTable
                            (
                                exercise TEXT NOT NULL,
                                subject  TEXT NOT NULL,
                                PRIMARY KEY (exercise, subject)
                            )
                            """)

        self.connection.commit()

    # =========================
    # 通用工具
    # =========================
    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()

    # =========================
    # ✅ ORM 统一接口
    # =========================
    def _orm_fields(self, obj):
        return {
            "id": obj.id,
            "subject": obj.subject,
            "data_type": obj.data_type,
            "data": obj.data,
            "start_time": obj.start_time,
            "finish_time": obj.finish_time,
            "finish_time_type": obj.finish_time_type,
        }

    def add(self, obj: Assignment, table: str = "AssignmentTable"):
        """
        通用 ORM 插入
        helper.add(assignment, table="AssignmentRecord")
        """
        if table not in ("AssignmentTable", "AssignmentRecord"):
            raise ValueError(f"Invalid table name: {table}")

        fields = self._orm_fields(obj)
        columns = [k for k in fields if k != "id" or fields[k] is not None]
        values = [fields[k] for k in columns]

        placeholders = ", ".join(["?"] * len(columns))

        sql = f"""
        INSERT INTO {table} ({', '.join(columns)})
        VALUES ({placeholders})
        """

        self.cursor.execute(sql, values)
        self.commit()
        return self.cursor.lastrowid

    # =========================
    # Assignment 查询
    # =========================
    def get_by_subject(self, subject: str, table: str = "AssignmentTable") -> list[Assignment]:
        if table not in ("AssignmentTable", "AssignmentRecord"):
            raise ValueError(f"Invalid table name: {table}")

        self.cursor.execute(
            f"SELECT * FROM {table} WHERE subject = ?",
            (subject,)
        )

        rows = self.cursor.fetchall()
        result = []

        for row in rows:
            result.append(Assignment(
                id=row[0],
                subject=row[1],
                data_type=row[2],
                data=row[3],
                start_time=row[4],
                finish_time=row[5],
                finish_time_type=row[6]
            ))

        return result

    # =========================
    # ExerciseSubjectTable（保留但未在 ORM 中使用）
    # =========================
    def bind_exercise_subject(self, exercise, subject):
        self.cursor.execute("""
        INSERT OR REPLACE INTO ExerciseSubjectTable (exercise, subject)
        VALUES (?, ?)
        """, (exercise, subject))
        self.commit()

    def unbind_exercise_subject(self, exercise, subject):
        self.cursor.execute("""
                            DELETE
                            FROM ExerciseSubjectTable
                            WHERE exercise = ?
                              AND subject = ?
                            """, (exercise, subject))
        self.commit()

    def get_subjects_by_exercise(self, exercise):
        self.cursor.execute(
            "SELECT subject FROM ExerciseSubjectTable WHERE exercise = ?",
            (exercise,)
        )
        return [row[0] for row in self.cursor.fetchall()]

    def get_exercises_by_subject(self, subject):
        self.cursor.execute(
            "SELECT exercise FROM ExerciseSubjectTable WHERE subject = ?",
            (subject,)
        )
        return [row[0] for row in self.cursor.fetchall()]


class AgendaXServer:
    _event = threading.Event()
    _time_out = 0.0
    _time_out_times = 0
    _tick_second = 0.0
    _tick_per_second = 1.0
    _tasks: list[Task] = []
    _major_tasks: list[Task] = []

    def _exec(self, task: Task) -> None:
        start = time.time()
        task.execute()
        end = time.time()
        self._tick_second += end - start
        print(self._tick_second)

    def __init__(self):
        self.database = DatabaseHelper()
        self.settings = Settings()

    def _resume(self):
        self._event.set()

    def main(self):
        is_time_out = False
        for major_task in self._major_tasks:
            if is_time_out:
                break
            self._exec(major_task)
            is_time_out = self.handle_timeout()

        for task in self._tasks:
            if is_time_out:
                break
            self._exec(task)
            is_time_out = self.handle_timeout()

        if not is_time_out:
            self._event.wait(self._tick_per_second - self._tick_second)

    def handle_timeout(self):
        if (len(self._major_tasks) > 0 or len(self._tasks) > 0) and self._tick_second > self._tick_per_second:
            self._time_out_times += 1
            self._time_out += self._tick_second - self._tick_per_second
            self._tick_second = 0.0
            if self._time_out_times >= 50:
                LOG.warning(
                    f"Can't keep up! Is the server overloaded? Running {int(self._time_out * 1000)} ms or {self._time_out // self._tick_per_second} ticks behind.")
                self._time_out_times = 0
                self._time_out = 0.0
            return True
        return False
