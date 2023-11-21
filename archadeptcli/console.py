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

# Third-party deps
from rich.align import Align as RichAlign
from rich.console import Console as RichConsole, Group as RichGroup
from rich.panel import Panel as RichPanel

class Console():
    """ Wrapper around upstream Rich Console used for all textual output. """

    def __init__(self, debug:bool=False) -> None:
        """ Constructor.

        Parameters
        ----------
        debug
            Whether to enable logging debug messages.
        """

        self.debug_enabled = debug
        """ Whether debug logging is enabled. See also: :meth:`Console.debug`. """

        self.rich_console = RichConsole()
        """ Underlying Rich Console object. """

    def print(self, *args, **kwargs) -> None:
        """ Print to the console.

        Parameters
        ----------
        Same as for :meth:`~rich.Console.print`.
        """
        self.rich_console.print(*args, **kwargs)

    def debug(self, *args, **kwargs) -> None:
        """ Print to the console, but only if debug logging is enabled.

        Parameters
        ----------
        Same as for :meth:`~rich.Console.print`.
        """
        if self.debug_enabled:
            self.rich_console.print(*args, **kwargs)

_console:Optional[Console] = None
""" Global Console singleton. """

def init(debug:bool=False) -> None:
    """ Initialize the ``console.py`` module.

    Parameters
    ----------
    debug
        Whether to enable logging debug messages.
    """
    global _console
    _console = Console(debug=debug)

def getConsole() -> Console:
    """ Get a handle to the global Console singleton. """
    global _console
    return _console

__all__ = [
    'init',
    'Console',
    'getConsole',
    'RichAlign',
    'RichConsole',
    'RichGroup',
    'RichPanel',
]

