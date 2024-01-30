"""
Copyright © 2023, ARCHADEPT LTD. All Rights Reserved.

License: MIT

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

# Standard deps
from typing import Optional

# Local deps
from .console import getConsole

class ArchAdeptError(Exception):
    """ Base class of all exceptions raised by the ArchAdept CLI. """

    unique_id:int = 0xE000
    """ Unique ID of this exception class. """

    is_bug:bool = False
    """ Whether this exception class represents a bug in the ArchAdept CLI. """

    def __init__(self, message:Optional[str]=None) -> None:
        """ Constructor.

        Parameters
        ----------
        message
            Contextual message to log for this exception.
        """
        super().__init__()
        self.message = message

    def __str__(self) -> str:
        """ Render this exception's error message. """
        s = f'[ArchAdept error 0x{self.unique_id:04X}] '
        if self.message is not None:
            s += f'{self.message}{"." if self.message[-1] not in ".!?" else ""}'
        s += '\n\n'
        if self.is_bug:
            s += f'This looks like a bug in archadeptcli :-(\n\nPlease submit a bug ' \
                 f'report to support@archadept.com or raise an issue on the GitHub ' \
                 f'repository at https://github.com/ArchAdept/archadeptcli.'
        else:
            s += f'See https://archadept.com/help/errors for more help with this error.'
        if not getConsole().debug_enabled:
            s += f'\n\nNote: You can also rerun with `-v` for more verbose debug logging.'
        return s

class UngracefulExit(ArchAdeptError):
    """ Raised when we crash due to any kind of uncaught exception. """
    unique_id = 0xEAA1
    is_bug = True

class InternalError(ArchAdeptError):
    """ Raised on fatal internal error. """
    unique_id = 0xEAA2
    is_bug = True

class DockerNotFound(ArchAdeptError):
    """ Raised when we fail to find the Docker CLI binary. """
    unique_id = 0xEDC1
    is_bug = False

class DockerEngineNotRunning(ArchAdeptError):
    """ Raised when the Docker Engine is not currently running. """
    unique_id = 0xEDC2
    is_bug = False

class DockerServerError(ArchAdeptError):
    """ Raised when a Docker CLI invocation unexpectedly fails. """
    unique_id = 0xEDC3
    is_bug = False

class SimulationError(ArchAdeptError):
    """ Raised when something goes wrong with running a QEMU simulation. """
    unique_id = 0xEDC4
    is_bug = False

class DockerContainerError(ArchAdeptError):
    """ Raised when a Docker container does not have the expected attributes. """
    unique_id = 0xEDC5
    is_bug = False

__all__ = [
    'ArchAdeptError',
    'UngracefulExit',
    'InternalError',
    'DockerNotFound',
    'DockerEngineNotRunning',
    'DockerServerError',
    'SimulationError',
]

