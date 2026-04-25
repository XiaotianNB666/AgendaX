import socket
import threading
import time
import uuid
import base64
from typing import Optional, Callable, override, List

from core.server.packets import HelloPacket, JSONPacket, ResourceRequestPacket, Packet, ResourceResponsePacket, \
    CrashPacket
from core.server.server import AgendaXServer, Assignment, ServerState
from core.app import LOG, version


class RemoteServer(AgendaXServer):
    def __init__(self, remote_host: str = "localhost", remote_port: int = 2000):
        # 不创建本地监听 socket（作为客户端）
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.remote_socket: Optional[socket.socket] = None
        self.is_connected = False
        self._connection_thread: Optional[threading.Thread] = None
        # action -> handler callable
        self._response_handlers: dict[str, Callable] = {}
        super().__init__(create_socket=False)

    # 覆写 start，使之作为客户端启动
    def start(self):
        if self._state != ServerState.INIT:
            raise RuntimeError("RemoteServer already started")
        self._state = ServerState.RUNNING
        try:
            self.connect_to_remote()
        except Exception as e:
            self.LOG.error(f"Failed to start RemoteServer: {e}", exc_info=True)
            self.shutdown()

    def shutdown(self):
        if self._state != ServerState.RUNNING:
            return

        self.LOG.info("Stopping RemoteServer...")
        self._state = ServerState.STOPPING

        try:
            self._executor.shutdown(wait=True)
        except Exception as e:
            self.LOG.debug(f"Executor shutdown error in RemoteServer: {e}", exc_info=True)

        # 断开远程连接（优雅关闭 socket）
        self.disconnect_remote()

        self._state = ServerState.STOPPED
        self.LOG.info("RemoteServer stopped.")

    def connect_to_remote(self):
        """连接到远程服务器"""
        if self.is_connected:
            return
        try:
            self.remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.remote_socket.settimeout(None)
            self.remote_socket.connect((self.remote_host, self.remote_port))
            self.is_connected = True
            self.LOG.info(f"Connected to remote server at {self.remote_host}:{self.remote_port}")
            # 启动监听线程读取 packet 协议的数据
            self._connection_thread = threading.Thread(target=self._listen_remote, daemon=True)
            self._connection_thread.start()
        except Exception as e:
            self.LOG.error(f"Failed to connect to remote server: {e}", exc_info=True)
            self.is_connected = False
            # 保证 remote_socket 被清理
            if self.remote_socket:
                try:
                    self.remote_socket.close()
                except Exception:
                    pass
                self.remote_socket = None

    def disconnect_remote(self):
        """断开远程连接，优雅关闭 socket（先 shutdown 再 close）"""
        if self.remote_socket:
            try:
                # 先尝试 shutdown，忽略在已关闭 socket 上的错误
                try:
                    self.remote_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                except Exception:
                    pass
                self.remote_socket.close()
            except Exception:
                pass
            finally:
                self.remote_socket = None
        self.is_connected = False
        self.LOG.info("Disconnected from remote server")

    def send_request(self, action: str, data: dict):
        """发送请求到远程服务器，使用 Packet 协议（JSONPacket）"""
        if not self.is_connected or not self.remote_socket:
            self.LOG.warning("Not connected to remote server")
            return
        try:
            payload = {"action": action, "data": data, "request_id": uuid.uuid4().hex}
            packet = JSONPacket.create(payload)
            self.send_packet(self.remote_socket, packet)
        except Exception as e:
            self.LOG.error(f"Failed to send request: {e}", exc_info=True)

    def request_resource(self, resource_type: str, identifier: str,
                         resource_response_handler: Optional[Callable] = None) -> bool:
        """通过 ResourceRequestPacket 请求资源（例如 data_type='file:img'）"""
        if not self.is_connected or not self.remote_socket:
            self.LOG.warning("Not connected to remote server")
            return False
        try:
            packet = ResourceRequestPacket.create(resource_type, identifier)
            self.send_packet(self.remote_socket, packet)
            self._response_handlers[identifier] = resource_response_handler
            return True
        except Exception as e:
            self.LOG.error(f"Failed to request resource: {e}", exc_info=True)
            return False

    def _listen_remote(self):
        while self._state == ServerState.RUNNING and self.is_connected and self.remote_socket:
            try:
                packet = self.wait_for_next_packet(self.remote_socket)
                if packet is None:
                    continue
                elif isinstance(packet, HelloPacket):
                    _version, _display_name = packet.get_value()
                    if _version != version():
                        LOG.warning(f"Remote server version mismatch: expected {version()}, got {_version}")
                    else:
                        LOG.info(f"Remote server version: {packet.get_value()}")
                elif isinstance(packet, ResourceResponsePacket):
                    try:
                        identifier, data = packet.get_value()
                        handler = self._response_handlers.get(identifier)
                        if handler:
                            handler(data)
                    except Exception:
                        self.LOG.exception("Error handling resource response packet")
                elif isinstance(packet, CrashPacket):
                    try:
                        crash_info = packet.get_value()
                    except Exception:
                        self.LOG.exception("Error handling crash packet")
            except (ConnectionAbortedError, ConnectionResetError, RuntimeError) as e:
                self.LOG.info(f"Remote connection closed: {e}")
                break
            except Exception as e:
                self.LOG.error(f"Error listening to remote: {e}", exc_info=True)
                break
        # 退出循环后确保断开资源
        try:
            self.disconnect_remote()
        except Exception:
            pass

    def sync_assignments(self, subject: str):
        """同步指定科目的任务"""
        self.send_request("get_assignments", {"subject": subject})

    def add_remote_assignment(self, assignment: Assignment):
        """添加任务到远程服务器"""
        data = {
            "subject": assignment.subject,
            "data_type": assignment.data_type,
            "data": assignment.data,
            "start_time": assignment.start_time,
            "finish_time": assignment.finish_time,
            "finish_time_type": assignment.finish_time_type,
        }
        self.send_request("add_assignment", data)

    def list_assignments(self, subject: Optional[str] = None, timeout: float = 5.0) -> List[Assignment]:
        """
        同步方式尝试从远程获取 assignment 列表。
        - 发送 action 'get_assignments'
        - 响应 action 名称：'resource_response'
        返回 Assignment 列表（超时或无响应返回空列表）
        """
        if not self.is_connected:
            self.LOG.warning("Not connected to remote server when listing assignments")
            return []

        ev = threading.Event()
        result = {"data": None}

        def _on_resp(data):
            try:
                result["data"] = data
            finally:
                ev.set()

        candidate_actions = ("assignments", "get_assignments", "get_assignments_response")
        # 保存并临时覆盖可能已有 handler，以便恢复
        original_handlers = {}
        for act in candidate_actions:
            original_handlers[act] = self._response_handlers.get(act)
            self.register_response_handler(act, _on_resp)

        try:
            self.send_request("get_assignments", {"subject": subject})
            ev.wait(timeout)
        finally:
            # 恢复原有 handlers（可能为 None）
            for act in candidate_actions:
                self.unregister_response_handler(act, original_handlers.get(act))

        data = result.get("data")
        if not data:
            return []

        assignments: List[Assignment] = []
        try:
            # 期望 data 为可迭代容器（list）或单个对象
            items = data if isinstance(data, (list, tuple)) else [data]
            for it in items:
                if isinstance(it, dict):
                    # 兼容 server 返回字典结构
                    try:
                        a = Assignment(
                            subject=it.get("subject", ""),
                            data_type=it.get("data_type", ""),
                            data=it.get("data", ""),
                            start_time=it.get("start_time", time.time()),
                            finish_time=it.get("finish_time"),
                            finish_time_type=it.get("finish_time_type", ""),
                            id=it.get("id")
                        )
                        assignments.append(a)
                    except Exception:
                        # 忽略单条转换失败
                        self.LOG.debug("Failed to convert assignment dict", exc_info=True)
                elif isinstance(it, Assignment):
                    assignments.append(it)
                else:
                    # 最后尝试直接解析为字符串或其他可用表示
                    try:
                        # 如果是简单字符串，放到 subject
                        assignments.append(Assignment(subject=str(it), data_type="", data=""))
                    except Exception:
                        continue
        except Exception:
            self.LOG.exception("Error parsing assignments response")
        return assignments

    def request_resource_sync(self, resource_type: str, identifier: str, timeout: float = 5.0) -> Optional[bytes]:
        """
        同步请求资源（例如 data_type='file:img'）。
        期望服务器以 JSONPacket 返回形如:
            { "action": "resource" | "resource_response", "data": {"identifier": ..., "content": "<base64>"} }
        或者直接以 JSONPacket 返回 data 为 base64 字符串。
        返回 bytes（解码后）或 None（超时/失败）。
        """
        if not self.is_connected:
            self.LOG.warning("Not connected to remote server when requesting resource")
            return None

        ev = threading.Event()
        result = {"data": None}

        def _on_resp(data):
            try:
                result["data"] = data
            finally:
                ev.set()

        candidate_actions = ("resource", "resource_response", "resource_request_response")
        original_handlers = {}
        for act in candidate_actions:
            original_handlers[act] = self._response_handlers.get(act)
            self.register_response_handler(act, _on_resp)

        try:
            # 使用 ResourceRequestPacket 发送
            packet = ResourceRequestPacket.create(resource_type, identifier)
            self.send_packet(self.remote_socket, packet)
            ev.wait(timeout)
        finally:
            for act in candidate_actions:
                self.unregister_response_handler(act, original_handlers.get(act))

        data = result.get("data")
        if data is None:
            return None

        # 处理返回格式
        try:
            # 如果 data 是 dict 且含 content 字段（base64）
            if isinstance(data, dict):
                content = data.get("content") or data.get("data") or data.get("content_base64")
                if isinstance(content, str):
                    try:
                        return base64.b64decode(content)
                    except Exception:
                        # 如果无法 base64 解码，尝试直接返回 utf-8 bytes
                        return content.encode("utf-8")
                # 如果服务器直接返回 bytes（不常见），尝试返回原样
                if isinstance(content, (bytes, bytearray)):
                    return bytes(content)
                # 若 data 直接是可序列化的字符串
            if isinstance(data, str):
                try:
                    return base64.b64decode(data)
                except Exception:
                    return data.encode("utf-8")
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
        except Exception:
            self.LOG.exception("Failed to parse resource response")

        return None

    @override
    def __str__(self):
        return f"RemoteServer(remote_host={self.remote_host}, remote_port={self.remote_port}, is_connected={self.is_connected})"

    @override
    def send_packet(self, client: socket = None, packet: Packet = None):
        if client is None:
            client = self.remote_socket
        if packet is None:
            return
        super().send_packet(client, packet)

    @property
    def is_connected(self) -> bool:
        return False
