from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable

from twisted.conch.ssh import channel, common, connection, transport, userauth
from twisted.internet import defer, protocol
from twisted.internet import reactor

if TYPE_CHECKING:
    from twisted.internet.interfaces import IAddress


class PasswordAuth(userauth.SSHUserAuthClient):
    def __init__(self, user: str, password: str, conn: Any) -> None:
        super().__init__(user, conn)
        self.password = password

    def getPassword(self, prompt: str | None = None) -> defer.Deferred:
        return defer.succeed(self.password)


class CommandChannel(channel.SSHChannel):
    name = b"session"

    def __init__(
        self,
        command: bytes,
        done_deferred: defer.Deferred,
        callback: Callable[[bytes], Any] | None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.command: bytes = command
        self.done_deferred: defer.Deferred = done_deferred
        self.callback: Callable[[bytes], Any] | None = callback

        self.data: bytes = b""

    def channelOpen(self, specificData: bytes) -> None:
        assert self.conn is not None
        self.conn.sendRequest(self, "exec", common.NS(self.command), wantReply=True)

    def dataReceived(self, data: bytes) -> None:
        self.data += data

    def extReceived(self, dataType: int, data: bytes) -> None:
        self.data += data

    def closeReceived(self) -> None:
        self.conn.transport.loseConnection()
        self.done_deferred.callback(self.data)

        # call the request client callback, if any
        if self.callback:
            self.callback(self.data)


class ClientConnection(connection.SSHConnection):
    def __init__(
        self,
        cmd: bytes,
        done_deferred: defer.Deferred,
        callback: Callable[[bytes], Any] | None,
    ) -> None:
        super().__init__()
        self.command: bytes = cmd
        self.done_deferred: defer.Deferred = done_deferred
        self.callback: Callable[[bytes], Any] | None = callback

    def serviceStarted(self) -> None:
        self.openChannel(
            CommandChannel(self.command, self.done_deferred, self.callback, conn=self)
        )


class ClientCommandTransport(transport.SSHClientTransport):
    def __init__(
        self,
        username: str,
        password: str,
        command: bytes,
        done_deferred: defer.Deferred,
        callback: Callable[[bytes], Any] | None,
    ) -> None:
        self.username: str = username
        self.password: str = password
        self.command: bytes = command
        self.done_deferred: defer.Deferred = done_deferred
        self.callback: Callable[[bytes], Any] | None = callback

    def verifyHostKey(self, hostKey: Any, fingerprint: str) -> defer.Deferred:
        return defer.succeed(True)

    def connectionSecure(self) -> None:
        self.requestService(
            PasswordAuth(
                self.username,
                self.password,
                ClientConnection(self.command, self.done_deferred, self.callback),
            )
        )


class ClientCommandFactory(protocol.ClientFactory):
    def __init__(
        self,
        username: str,
        password: str,
        command: bytes,
        done_deferred: defer.Deferred,
        callback: Callable[[bytes], Any] | None,
    ) -> None:
        self.username: str = username
        self.password: str = password
        self.command: bytes = command
        self.done_deferred: defer.Deferred = done_deferred
        self.callback: Callable[[bytes], Any] | None = callback

    def buildProtocol(self, addr: IAddress) -> ClientCommandTransport:
        return ClientCommandTransport(
            self.username,
            self.password,
            self.command,
            self.done_deferred,
            self.callback,
        )


def execute_ssh(
    host: str,
    port: int,
    username: str,
    password: str,
    command: bytes,
    callback: Callable[[bytes], Any] | None = None,
) -> defer.Deferred:
    done_deferred: defer.Deferred = defer.Deferred()

    factory = ClientCommandFactory(username, password, command, done_deferred, callback)
    reactor.connectTCP(host, port, factory)

    return done_deferred
