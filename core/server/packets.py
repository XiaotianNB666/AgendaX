from abc import ABC, abstractmethod
import json
from typing import Optional

from core.utils.dict_utils import get_key_from_value


def _generate_packet_bytes(packet: int, data: bytes):
    type_data = int.to_bytes(packet, 4, byteorder='big', signed=True)
    return type_data + data


class Packet(ABC):
    def __init__(self, data_type: str, data: bytes):
        self.data = data
        self.data_type = data_type

    def __repr__(self):
        return f"Packet(data={self.data})"

    @abstractmethod
    def get_value(self):
        ...

    @abstractmethod
    def to_bytes(self) -> bytes:
        ...

    @classmethod
    @abstractmethod
    def type(cls) -> str:
        ...

    @classmethod
    @abstractmethod
    def create(cls, *args) -> 'Packet':
        ...


class ShutdownPacket(Packet):
    @classmethod
    def create(cls):
        return cls(cls.type(), f'shutdown'.encode('utf-8'))

    @classmethod
    def type(cls):
        return "shutdown"

    def get_value(self):
        pass

    def to_bytes(self) -> bytes:
        return _generate_packet_bytes(get_key_from_value(PACKETS, ShutdownPacket), self.data)


class HelloPacket(Packet):
    @classmethod
    def type(cls):
        return "hello"

    @classmethod
    def create(cls):
        from core.app import version

        return cls(cls.type(), f'{version()}'.encode('utf-8'))

    def get_value(self):
        return self.data.decode('utf-8')

    def to_bytes(self) -> bytes:
        return _generate_packet_bytes(get_key_from_value(PACKETS, HelloPacket), self.data)


class StringPacket(Packet):
    @classmethod
    def type(cls):
        return "string"

    @classmethod
    def create(cls, s: str):
        return cls(cls.type(), s.encode('utf-8'))

    def get_value(self):
        return self.data.decode('utf-8')

    def to_bytes(self) -> bytes:
        return _generate_packet_bytes(get_key_from_value(PACKETS, StringPacket), self.data)


class IntPacket(Packet):
    @classmethod
    def type(cls):
        return "int"

    @classmethod
    def create(cls, i: int):
        return cls(cls.type(), int.to_bytes(i, byteorder='big', signed=True))

    def get_value(self):
        return int.from_bytes(self.data, byteorder='big', signed=True)

    def to_bytes(self) -> bytes:
        return _generate_packet_bytes(get_key_from_value(PACKETS, IntPacket), self.data)


class MessagePacket(StringPacket):
    @classmethod
    def type(cls):
        return "message"

    def to_bytes(self) -> bytes:
        return _generate_packet_bytes(get_key_from_value(PACKETS, MessagePacket), self.data)


class JSONPacket(Packet):
    @classmethod
    def type(cls):
        return "json"

    def get_value(self):
        return json.loads(self.data.decode('utf-8'))

    def to_bytes(self) -> bytes:
        return _generate_packet_bytes(get_key_from_value(PACKETS, JSONPacket), self.data)

    @classmethod
    def create(cls, d: dict) -> 'Packet':
        return cls(cls.type(), json.dumps(d).encode('utf-8'))


class CrashPacket(JSONPacket):
    @classmethod
    def type(cls):
        return "crash"

    def to_bytes(self) -> bytes:
        return _generate_packet_bytes(get_key_from_value(PACKETS, CrashPacket), self.data)

    def get_value(self):
        from core.crash_report import StaticCrashReport
        report_struct = self.data.decode('utf-8')
        report_dict = json.loads(report_struct)
        return StaticCrashReport(
            report_string=report_dict['report_string'],
            report_title=report_dict['report_title'],
            formated_time=report_dict['formated_time'],
            trace_string=report_dict['trace_string'],
            var_monitor_string=report_dict['var_monitor_string']
        )

    @classmethod
    def create(cls, crash_report) -> 'Packet':
        report_struct = {
            'report_string': crash_report.string,
            'report_title': crash_report.report_title,
            'formated_time': crash_report.formated_time,
            'trace_string': crash_report.trace_string,
            'var_monitor_string': crash_report.var_monitor_string
        }
        return super().create(report_struct)


class AssignmentPacket(JSONPacket):
    @classmethod
    def type(cls):
        return "assignment"

    @classmethod
    def create(cls, assignment) -> Packet:
        assignment_dict = {
            'subject': assignment.subject,
            'data_type': assignment.data_type,
            'data': assignment.data,
            'start_time': assignment.start_time,
            'finish_time': assignment.finish_time,
            'finish_time_type': assignment.finish_time_type
        }
        return super().create(assignment_dict)

    def get_value(self):
        assignment_dict = super().get_value()
        from core.server.server import Assignment
        return Assignment(
            subject=assignment_dict['subject'],
            data_type=assignment_dict['data_type'],
            data=assignment_dict['data'],
            start_time=assignment_dict['start_time'],
            finish_time=assignment_dict.get('finish_time'),
            finish_time_type=assignment_dict.get('finish_time_type', "")
        )


class AssignmentDelPacket(IntPacket):
    @classmethod
    def type(cls):
        return "assignment_del"

    @classmethod
    def create(cls, assignment):
        from core.server.server import Assignment
        assignment: Assignment
        return super().create(assignment.id)

    def _to_bytes(self) -> bytes:
        return _generate_packet_bytes(get_key_from_value(PACKETS, AssignmentDelPacket), self.data)


class ResourceRequestPacket(JSONPacket):
    def to_bytes(self) -> bytes:
        return _generate_packet_bytes(get_key_from_value(PACKETS, ResourceRequestPacket), self.data)

    @classmethod
    def type(cls):
        return "resource_request"

    @classmethod
    def create(cls, resource_type: str, identifier: str) -> Packet:
        """
        resource_type: 比如 "file:img"
        identifier: 资源标识（例如文件路径或 id）
        """
        payload = {
            "resource_type": resource_type,
            "identifier": identifier
        }
        return super().create(payload)

    def get_value(self):
        return super().get_value()


class ResourceResponsePacket(Packet):
    def to_bytes(self) -> bytes:
        return _generate_packet_bytes(get_key_from_value(PACKETS, ResourceResponsePacket), self.data)

    @classmethod
    def type(cls):
        return "resource_response"

    @classmethod
    def create(cls, identifier: str, data: bytes) -> Packet:
        return cls(cls.type(), identifier.encode('utf-8') + b'\x00\x00' + data)

    def get_value(self) -> tuple[Optional[str], bytes]:
        """
        返回 (identifier, data)，如果没有 identifier 则返回 (None, data)
        """
        # 若有第一个\x00\x00，则认为前面是 identifier，后面是数据；否则全部当作数据
        if b'\x00\x00' in self.data:
            identifier_bytes, data = self.data.split(b'\x00\x00', 1)
            identifier = identifier_bytes.decode('utf-8')
            return identifier, data
        else:
            return None, self.data


class HeadPacket(Packet):
    def get_value(self) -> int:
        return int.from_bytes(self.data[4:], byteorder='big', signed=True)

    def to_bytes(self) -> bytes:
        return _generate_packet_bytes(get_key_from_value(PACKETS, HeadPacket), self.data)

    @classmethod
    def create(cls, p: Packet) -> 'Packet':
        packet_length = len(p.to_bytes())
        return cls(p.type(), int.to_bytes(packet_length, 16, byteorder='big', signed=True))

    @classmethod
    def type(cls) -> str:
        return "head"

    @classmethod
    def length(cls) -> int:
        return 4 + 16  # packet id + data length


PACKETS: dict[int, type[Packet]] = {
    -1: HeadPacket,
    0: None,  # 0 号包保留，表示无效包
    1: HelloPacket,
    2: ShutdownPacket,
    3: StringPacket,
    4: MessagePacket,
    5: JSONPacket,
    6: CrashPacket,
    7: AssignmentPacket,
    8: ResourceRequestPacket,
    9: AssignmentDelPacket,
    10: IntPacket,
    11: ResourceResponsePacket
}


def get_packet(data: bytes):  # 前32个bit(int32)为packet id，后面为数据
    if len(data) < 4:
        raise ValueError("Invalid packet data: too short")
    # 解析 packet id
    packet_id = int.from_bytes(data[:4], byteorder='big', signed=True)
    if packet_id not in PACKETS or packet_id == 0:
        raise ValueError(f"Invalid packet id: {packet_id}")

    data = data[4:]
    packet_cls = PACKETS[packet_id]
    return packet_cls(packet_cls.type(), data)
