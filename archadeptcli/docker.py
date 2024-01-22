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
import json
import platform
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Local deps
from .console import getConsole, RichGroup, RichPanel
from .exceptions import *

@dataclass
class DockerCLIResult():
    """ Class representing the result of invoking the Docker CLI. """

    command:Optional[str]=None
    """ The full Docker CLI command that was invoked. """

    returncode:int = 0
    """ Shell exit status of the Docker CLI invocation. """

    output:Optional[str]=None
    """ Docker CLI invocation's captured and combined ``stdout`` plus ``stderr``
        if the Docker CLI was invoked with ``capture=True``, else ``None``. """

class DockerCLIWrapper():
    """ Wrapper around the Docker CLI enabling us to create, manage, and run
        Docker containers. """

    def __init__(self):
        """ Constructor. """

        self.guest_workdir:Path = Path('/mnt/archadept-workdir')
        """ Where to mount the host-side working directory inside any spawned
            Docker containers. """

        self.label:str = 'com.archadept.container'
        """ Label used to identify containers spawned by the ArchAdept CLI. """

        self.docker_cli_binary:Path = shutil.which('docker')
        """ Path to the Docker CLI binary. """

        # Validate we actually found the Docker CLI binary, and turn it into a Path object.
        if self.docker_cli_binary is None:
            raise DockerNotFound('failed to find `docker` CLI binary, is Docker installed and available on $PATH?')
        self.docker_cli_binary = Path(self.docker_cli_binary)

        if not self.docker_engine_is_running():
            raise DockerEngineNotRunning(f'Docker Engine not running, please start it and try again')

    def invoke(self, command:str, capture:bool=False) -> DockerCLIResult:
        """ Invoke the Docker CLI.

        Parameters
        ----------
        command
            The command to invoke, sans the leading ``docker``.
              Example: ``run archadept/example-code-tools:latest gcc -dumpmachine``
        capture
            The default behavior with ``capture=False`` is to directly attach the
            host terminal's ``stdin``, ``stdout``, and ``stderr`` to the subprocess
            in which we are invoking the Docker CLI. Pass ``capture=True`` to instead
            capture the subprocess's combined ``stdout`` and ``stderr`` in the
            ``ouput`` field of the returned ``DockerCLIResult``.

        Warning
        -------
        Care must be taken not to pass ``capture=True`` if the ``command`` is
        interactive and/or expects to control the host terminal, such as when
        running a Curses-based application or interactive GDB debugger session
        inside a Docker container. In these cases, no output will be displayed
        in the host terminal which would be rather confusing for the user.

        Returns
        -------
        The shell exit status of the Docker CLI invocation and, if ``capture=True``,
        its captured and combined ``stdout`` plus ``stderr``, else ``None``.
        """
        full_command = f'{self.docker_cli_binary} {command}'.rstrip()
        getConsole().debug(RichPanel.fit(full_command, style='white', title='invoking command...'))
        # Spawn the subprocess with appropriate piping.
        output = None
        kwargs = {'text':True, 'encoding':'UTF-8'}
        if capture:
            kwargs['stdout'] = subprocess.PIPE
            kwargs['stderr'] = subprocess.STDOUT
        if platform.system() == 'Windows':
            subprocess_command = full_command
        else:
            subprocess_command = shlex.split(full_command)
        with subprocess.Popen(subprocess_command, **kwargs) as p:
            # Run the subprocess to completion. How we accomplish this depends
            # on whether we're capturing the subprocess's output or we directly
            # attached the host terminal's ``stdin``, ``stdout``, and ``stderr``.
            if capture:
                (output, _) = p.communicate()
            else:
                while p.poll() is None:
                    continue
        if capture:
            output = output.strip()
        result = DockerCLIResult(command=full_command, returncode=p.returncode, output=output)
        # If we're capturing the subprocess's output then log it in full now
        # at debug verbosity before we start processing it in the caller.
        if capture:
            self.debug_cli_result(result)
        return result

    def _print_cli_result(self, result:DockerCLIResult, printer:callable) -> None:
        """ Underlying implementation of ``{print,debug,error}_cli_result()``;
            pretty-prints a ``DockerCLIResult``.

        Parameters
        ----------
        result
            The ``DockerCLIResult` to pretty-print.
        printer
            The :meth:`~rich.Console.print`-like function to use to print the
            ``DockerCLIResult``.
        """
        border_style = 'green' if result.returncode == 0 else 'red'
        printer(
            RichPanel.fit(
                RichGroup(
                    RichPanel.fit(
                        result.command,
                        title='command',
                        style='blue',
                    ),
                    RichPanel(
                        result.output,
                        title='output',
                        subtitle=f'returncode={result.returncode}',
                        border_style=border_style
                    ),
                ),
                border_style=border_style,
            )
        )

    def print_cli_result(self, result:DockerCLIResult) -> None:
        """ Unconditionally pretty-print a ``DockerCLIResult``.

        Parameters
        ----------
        result
            The ``DockerCLIResult`` to pretty-print.
        """
        self._print_cli_result(result, getConsole().print)

    def debug_cli_result(self, result:DockerCLIResult) -> None:
        """ Pretty-print a ``DockerCLIResult`` but only if debug logging is
            enabled.

        Parameters
        ----------
        result
            The ``DockerCLIResult` to pretty-print.
        """
        self._print_cli_result(result, getConsole().debug)

    def error_cli_result(self, result:DockerCLIResult) -> None:
        """ Pretty-print a ``DockerCLIResult``, but only if debug logging is
            *NOT* enabled.

        Parameters
        ----------
        result
            The ``DockerCLIResult`` to pretty-print
        """
        console = getConsole()
        if not console.debug_enabled:
            self._print_cli_result(result, console.print)

    def docker_engine_is_running(self) -> bool:
        """ Returns whether the Docker Engine is currently running. """
        return self.invoke('info', capture=True).returncode == 0

    def run(
        self,
        command:str,
        detached:bool=False,
        capture:bool=False,
        image:str='archadept/example-code-tools',
        tag:str='latest',
        host_workdir:Path=Path.cwd(),
        env:dict={},
    ) -> DockerCLIResult:
        """ Run a command in a new Docker container.

        Parameters
        ----------
        command
            The full command to execute in the Docker container.
        detached
            Whether to start the Docker container in detached state.
        capture
            Same as for :meth:`DockerCLIWrapper.invoke`. Treated as ``True`` when
            ``detached=True`` regardless of the provided value.
        image
            Docker image repository to use.
        tag
            Docker image tag to use.
        host_workdir
            Host-side working directory to mount inside the Docker container.
        env
            Dictionary of environment variable key-value pairs that will be
            exported to the Docker container.

        Returns
        -------
        ``DockerCLIResult`` containing the shell exit status of the underlying
        Docker CLI invocation and, if ``capture=True`` or ``detached=True``,
        its combined ``stdout`` and ``stderr`` output.
        """
        full_command =      f'run -it{"d" if detached else ""} --rm\n' \
                            f'  -v "{host_workdir}:{self.guest_workdir}"\n' \
                            f'  -w {self.guest_workdir}\n' \
                            f'  --label {self.label}\n'
        for k,v in env.items():
            full_command += f'  --env {k}={v}\n'
        full_command +=     f'  {image}:{tag}\n' \
                            f'  {command}\n'
        return self.invoke(full_command, capture=True if detached else capture)

    def attach(self, container_id:str, capture:bool=False) -> DockerCLIResult:
        """ Attach to a running container.

        Parameters
        ----------
        container_id
            ID of the Docker container to attach to.
        capture
            Same as for :meth:`DockerCLIWrapper.invoke`.

        Returns
        -------
        ``DockerCLIResult`` containing the shell exit status of the Docker
        container and, if ``capture=True``, its combined ``stdout`` and ``stderr``
        output.
        """
        return self.invoke(f'attach {container_id}', capture=capture)

    def exec(self, container_id:str, command:str, capture:bool=False) -> DockerCLIResult:
        """ Execute a command in a running container.

        Parameters
        ----------
        container_id
            ID of the Docker container to attach to.
        command
            The full command to execute in the Docker container.
        capture
            Same as for :meth:`DockerCLIWrapper.invoke`.

        Returns
        -------
        ``DockerCLIResult`` containing the shell exit status of the command and,
        if ``capture=True``, its combined ``stdout`` and ``stderr`` output.
        """
        full_command = f'exec -it\n' \
                       f'  -w {self.guest_workdir}\n' \
                       f'  {container_id}\n' \
                       f'  {command}'
        return self.invoke(full_command)

    def prune(self) -> None:
        """ Prune any lingering Docker containers that we may have failed to
            cleanup on previous runs. """
        result = self.invoke(f'ps --quiet --all --filter label={self.label}', capture=True)
        if result.returncode != 0:
            self.error_cli_result(result)
            raise DockerServerError('failed to query Docker process statuses')
        containers = result.output.strip()
        if not containers:
            return result
        containers = ' '.join(containers.splitlines())
        result = self.invoke(f'container rm --force {containers}', capture=True)
        if result.returncode != 0:
            self.error_cli_result(result)
            raise DockerServerError('failed to remove Docker containers')

    def get_project_dir(self, container_id:str) -> Path:
        """ Get the host-side path to the ArchAdept example project directory
            mounted inside a running Docker container.

        Parameters
        ----------
        container_id
            ID of the Docker container to attach to.

        Returns
        -------
        Path to the host-side ArchAdept example project directory.
        """
        result = self.invoke(f'container inspect {container_id}', capture=True)
        if result.returncode != 0:
            self.error_cli_result(result)
            raise DockerServerError('failed to inspect container')
        try:
            data = json.loads(result.output.strip())
        except json.decoder.JSONDecodeError as e:
            self.error_cli_result(result)
            raise DockerServerError('malformed Docker server response: expected valid JSON')
        if not isinstance(data, list) or len(data) != 1:
            self.error_cli_result(result)
            raise DockerServerError('malformed Docker server response: expected a list of length 1')
        if 'HostConfig' not in data[0] or 'Binds' not in data[0]['HostConfig']:
            self.error_cli_result(result)
            raise DockerServerError('malformed Docker server response: JSON missing [HostConfig][Binds] key')
        binds = data[0]['HostConfig']['Binds']
        if not isinstance(binds, list) or len(data) < 1:
            self.error_cli_result(result)
            raise DockerContainerError('container has no directories mounted in it')
        workdir = '/mnt/archadept-workdir'
        for bind in binds:
            if bind.endswith(workdir):
                return Path(bind[:-len(workdir)-1])
        raise DockerContainerError(f'container has no directory mounted at {workdir}')

