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
from .console import getConsole, RichAlign, RichGroup, RichPanel, Color


class ArchAdeptWarning():
    """ Base class of all warnings flagged by the ArchAdept CLI. """

    unique_id:int = 0x0400
    """ Unique ID of this warning class. """

    tips:list[str] = []
    """ Additional help info that will be displayed for this warning. """

    def __init__(self, message:Optional[str]=None) -> None:
        """ Constructor.

        Parameters
        ----------
        message
            Contextual message to log for this warning.
        """
        self.message = message
        self.render()

    def render(self) -> None:
        """ Render this warning, pretty-printing it to the console. """
        message = self.__class__.__name__
        if self.message is not None:
            message += f': {self.message}{"." if self.message[-1] not in ".!?" else ""}'
        renderables = [f'{message}\n']
        for tip in self.tips + ['Attempting to continue anyway, but this may not work as expected.']:
            renderables += [f'{tip}\n']
        renderables += ['See https://archadept.com/help/warnings for more help with this warning.']
        console = getConsole()
        console.print(RichPanel.fit(RichGroup(*renderables), style=Color.WARNING,
                                    title=f'ArchAdept warning 0x{self.unique_id:04X}'))
        if not console.debug_enabled:
            console.print(RichPanel.fit(f'Note: You can also rerun with `-v` for more verbose debug logging.', style=Color.WARNING))

class ProjectRunSupportUnknown(ArchAdeptWarning):
    """ Flagged when we are unable to determine whether an example project
        supports being run on QEMU. """
    unique_id = 0x443

class ProjectDoesNotSupportRun(ArchAdeptWarning):
    """ Flagged when an example project's config file explicitly states
        that we do not support running that project on QEMU. """
    unique_id = 0x444

class CommandLineCharacters(ArchAdeptWarning):
    """ Flagged when a command line appears to contain characters that
        may not behave consistently across platforms. """
    unique_id = 0x445
    tips = ['These characters are not guaranteed to behave consistently across Windows vs UNIX.']

class ArchAdeptError(Exception):
    """ Base class of all exceptions raised by the ArchAdept CLI. """

    unique_id:int = 0xE000
    """ Unique ID of this exception class. """

    is_bug:bool = False
    """ Whether this exception class represents a bug in the ArchAdept CLI. """

    tip:Optional[str] = None
    """ Additional help info that will be displayed for this exception. """

    def __init__(self, message:Optional[str]=None) -> None:
        """ Constructor.

        Parameters
        ----------
        message
            Contextual message to log for this exception.
        """
        super().__init__()
        self.message = message

    def render(self) -> None:
        """ Render this exception, pretty-printing it to the console. """
        message = self.__class__.__name__
        if self.message is not None:
            message += f': {self.message}{"." if self.message[-1] not in ".!?" else ""}'
        renderables = [f'{message}\n']
        if self.tip is not None:
            renderables += [f'{self.tip}\n']
        if self.is_bug:
            renderables += ['This looks like a bug in archadeptcli 😔\n',
                            'Please submit a bug report to support@archadept.com, or raise an issue',
                            'on the GitHub repository at https://github.com/ArchAdept/archadeptcli.']
        else:
            renderables += ['See https://archadept.com/help/errors for more help with this error.']
        console = getConsole()
        console.print(RichPanel.fit(RichGroup(*renderables), Color.ERROR,
                                    title=f'!!! ArchAdept error 0x{self.unique_id:04X} !!!'))
        if not console.debug_enabled:
            console.print(RichPanel.fit(f'Note: You can also rerun with `-v` for more verbose debug logging.', style=Color.ERROR))

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
    tip = 'Is Docker installed and the Docker CLI binary visible on your $PATH?'

class DockerEngineNotRunning(ArchAdeptError):
    """ Raised when the Docker Engine is not currently running. """
    unique_id = 0xEDC2
    is_bug = False
    tip = 'If you\'ve installed Docker Desktop, open it and ensure the Docker Engine is running.'

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
    'ArchAdeptWarning',
    'ProjectRunSupportUnknown',
    'ProjectDoesNotSupportRun',
    'CommandLineCharacters',
    'ArchAdeptError',
    'UngracefulExit',
    'InternalError',
    'DockerNotFound',
    'DockerEngineNotRunning',
    'DockerServerError',
    'SimulationError',
    'DockerContainerError',
]

