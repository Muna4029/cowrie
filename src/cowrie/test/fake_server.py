# Copyright (c) 2016 Dave Germiquet
# See LICENSE for details.

from __future__ import annotations

from typing import TYPE_CHECKING

from cowrie.shell import fs

if TYPE_CHECKING:
    from cowrie.shell.fs import HoneyPotFilesystem


class FakeServer:
    """FakeServer class.

    @ivar hostname Servers Host Name
    @ivar fs File System for cowrie to use
    """

    arch: str
    hostname: str
    fs: "HoneyPotFilesystem"
    process: None

    def __init__(self) -> None:
        self.arch = "linux-x64-lsb"
        self.hostname = "unitTest"

        self.fs = fs.HoneyPotFilesystem("arch", "/root")
        self.process = None


class FakeAvatar:
    """FakeAvatar class.

    @var avatar itself
    @ivar server server configuration
    @var fs File System for cowrie to use
    @var environ for user
    @var uid for user
    """

    avatar: "FakeAvatar"
    server: "FakeServer"
    uid: int
    gid: int
    home: str
    username: str
    environ: dict[str, str]
    windowSize: list[int]

    def __init__(self, server: "FakeServer") -> None:
        self.avatar = self
        self.server = server

        self.uid = 0
        self.gid = 0
        self.home = "/root"
        self.username = "root"
        self.environ = {
            "LOGNAME": self.username,
            "USER": self.username,
            "HOME": self.home,
            "TMOUT": "1800",
        }
        if self.uid == 0:
            self.environ["PATH"] = (
                "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
            )
        else:
            self.environ["PATH"] = (
                "/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games"
            )
        self.windowSize = [25, 80]
