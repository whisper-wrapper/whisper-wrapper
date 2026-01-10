"""IPC server for hotkey trigger commands."""

from typing import Callable, Optional

from PyQt6.QtNetwork import QLocalServer
from PyQt6.QtCore import QObject

from .logging_utils import get_logger

logger = get_logger("ipc")


class IpcServer(QObject):
    def __init__(self, socket_name: str, handler: Callable[[str], str], parent=None):
        super().__init__(parent)
        self._socket_name = socket_name
        self._handler = handler
        self._server: Optional[QLocalServer] = None

    def start(self) -> bool:
        QLocalServer.removeServer(self._socket_name)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._handle_connection)

        if not self._server.listen(self._socket_name):
            logger.error(f"Failed to start IPC server: {self._server.errorString()}")
            return False

        logger.info(f"IPC server listening on: {self._socket_name}")
        return True

    def _handle_connection(self):
        if not self._server:
            return
        socket = self._server.nextPendingConnection()
        if socket:
            socket.waitForReadyRead(1000)
            data = socket.readAll().data().decode("utf-8").strip()
            logger.debug(f"IPC received: {data}")
            response = self._handler(data)
            socket.write(response.encode())
            socket.flush()
            socket.disconnectFromServer()

    def close(self):
        if self._server:
            self._server.close()
