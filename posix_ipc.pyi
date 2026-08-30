from collections.abc import Callable
from typing import Any

# Module Functions

def unlink_semaphore(name: str) -> None: ...
def unlink_shared_memory(name: str) -> None: ...
def unlink_message_queue(name: str) -> None: ...

# Module Constants

O_CREX: int
O_CREAT: int
O_EXCL: int
O_TRUNC: int
PAGE_SIZE: int
SEMAPHORE_TIMEOUT_SUPPORTED: bool
SEMAPHORE_VALUE_SUPPORTED: bool
SEMAPHORE_VALUE_MAX: int
MESSAGE_QUEUES_SUPPORTED: bool
QUEUE_MESSAGES_MAX_DEFAULT: int
QUEUE_MESSAGE_SIZE_MAX_DEFAULT: int
QUEUE_PRIORITY_MAX: int
USER_SIGNAL_MIN: int
USER_SIGNAL_MAX: int
VERSION: str
O_NONBLOCK: int
O_RDONLY: int
O_RDWR: int
O_WRONLY: int
__license__: str
__version__: str
__copyright__: str
__author__: str

# Exceptions

class SignalError(Error):
    pass

class PermissionsError(Error):
    pass

class BusyError(Error):
    pass

class Error(Exception):
    pass

class ExistentialError(Error):
    pass

# Main Classes

class Semaphore:
    def __init__(self, name: str, flags: int = ..., mode: int = ..., initial_value: int = ...) -> None: ...
    def acquire(self, timeout: float | None = ...) -> None: ...
    def release(self) -> None: ...
    def close(self) -> None: ...
    def unlink(self) -> None: ...
    def __enter__(self) -> None: ...
    def __exit__(self) -> None: ...
    mode: int
    name: str
    value: int

class SharedMemory:
    def __init__(
        self, name: str, flags: int = ..., mode: int = ..., size: int = ..., read_only: bool = ...
    ) -> None: ...
    def close_fd(self) -> None: ...
    def fileno(self) -> None: ...
    def unlink(self) -> None: ...
    fd: int
    mode: int
    name: str
    size: int

class MessageQueue:
    def __init__(
        self,
        name: str | None,
        flags: int = ...,
        mode: int = ...,
        max_messages: int = ...,
        max_message_size: int = ...,
        read: bool = ...,
        write: bool = ...,
    ) -> None: ...
    def send(self, message: str | bytes, timeout: float | None = ..., priority: int = ...) -> None: ...
    def receive(self, timeout: float | None = ...) -> tuple[bytes, int]: ...
    def request_notification(self, notification: int | tuple[Callable[[Any], None], Any] | None = ...) -> None: ...
    def close(self) -> None: ...
    def fileno(self) -> None: ...
    def unlink(self) -> None: ...
    name: str
    mode: int
    mqd: int
    block: bool
    current_messages: int
    max_messages: int
    max_message_size: int
