from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from backend_pool.ssh_exec import execute_ssh
from backend_pool.telnet_exec import execute_telnet

from twisted.internet import defer


class ProxyTestCommand:
    """
    This class executes commands on Proxy instances and their backends (or either one of them).
    If executing on both, it compares their outputs, and a deferred succeeds on that case.
    """

    def __init__(
        self,
        connection_type: str,
        hostname: str,
        port_backend: int,
        port_proxy: int,
        username_backend: str,
        password_backend: str,
        username_proxy: str,
        password_proxy: str,
    ) -> None:
        self.deferred = defer.Deferred()
        self.backend_data: bytes | None = None
        self.proxy_data: bytes | None = None

        self.hostname = hostname
        self.port_backend = port_backend
        self.port_proxy = port_proxy

        self.username_backend = username_backend
        self.password_backend = password_backend
        self.username_proxy = username_proxy
        self.password_proxy = password_proxy

        # whether to execute the command via SSH or Telnet
        self.execute = execute_ssh if connection_type == "ssh" else execute_telnet

    def execute_both(self, command: bytes | str) -> None:
        def callback_backend(data: bytes) -> None:
            # if we haven't received data from the proxy just store the output
            if not self.proxy_data:
                self.backend_data = data
            else:
                # compare data from proxy and backend
                if data == self.proxy_data:
                    self.deferred.callback(True)
                else:
                    self.deferred.errback(ValueError())

        def callback_proxy(data: bytes) -> None:
            # if we haven't received data from the backend just store the output
            if not self.backend_data:
                self.proxy_data = data
            else:
                # compare data from proxy and backend
                if data == self.backend_data:
                    self.deferred.callback(True)
                else:
                    self.deferred.errback(
                        ValueError("Values from proxy and backend do not match!")
                    )

        # execute exec command on both backend and proxy
        self.execute(
            self.hostname,
            self.port_backend,
            self.username_backend,
            self.password_backend,
            command,
            callback_backend,
        )
        self.execute(
            self.hostname,
            self.port_proxy,
            self.username_proxy,
            self.password_proxy,
            command,
            callback_proxy,
        )

    def execute_one(
        self, is_proxy: bool, command: bytes | str, deferred: defer.Deferred
    ) -> None:
        def callback(data: bytes) -> None:
            deferred.callback(data)

        if is_proxy:
            # execute via proxy
            username = self.username_proxy
            password = self.password_proxy
        else:
            # execute via backend
            username = self.username_backend
            password = self.password_backend

        # execute exec command
        self.execute(
            self.hostname, self.port_backend, username, password, command, callback
        )
