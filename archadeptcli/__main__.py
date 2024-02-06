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
import argparse
import tomllib
from pathlib import Path
from typing import Any, Optional

# Third-party deps
import rich.traceback
rich.traceback.install(show_locals=True, suppress=[rich])

# Local deps
import archadeptcli
from archadeptcli.console import getConsole, RichAlign, RichGroup, RichPanel
from archadeptcli.docker import DockerCLIWrapper
from archadeptcli.exceptions import *

ARCHADEPTCLI_BASE_TAG = '1.1.4'
""" Current base tag of the archadeptcli repository. """

class CommandLineArgs():
    """ Class representing the arguments parsed from the command line. """

    def __init__(self):
        """ Parse command line arguments. """

        # Data-driven description which we use at runtime to programmatically
        # generate the various argument parsers. This also lets us share flags
        # and arguments between commands without duplicated code/logic.
        args_descr = {
            'commands': (
                {
                    'command': 'make',
                    'dict': {
                        'help': 'invoke project Makefile',
                        'description': 'Invokes an ArchAdept example project Makefile.',
                    },
                },
                {
                    'command': 'run',
                    'dict': {
                        'help': 'run project on simulated hardware',
                        'description': 'Runs an ArchAdept example project on a simulated Raspberry Pi 3b.',
                    },
                },
                {
                    'command': 'debug',
                    'dict': {
                        'help': 'attach debugger to live simulation',
                        'description': 'Attaches a GDB debug session to a live QEMU simulation started by `archadept run`.',
                    },
                },
                {
                    'command': 'prune',
                    'dict': {
                        'help': 'clean up any lingering Docker containers',
                        'description': 'Cleans up any lingering Docker containers from previous ArchAdept CLI invocations.',
                    },
                },
            ),
            'args': (
                {
                    'arg': '--version',
                    'top-level': True,
                    'dict': {
                        'dest': 'version',
                        'help': 'display archadeptcli version info',
                        'action': 'version',
                        'version': f'archadeptcli-v{ARCHADEPTCLI_BASE_TAG}',
                    },
                },
                {
                    'arg': '-v',
                    'top-level': True,
                    'dict': {
                        'dest': 'debug',
                        'help': 'enable logging verbose debug messages',
                        'action': 'store_true',
                    },
                },
                {
                    'arg': '-p',
                    'top-level': False,
                    'commands': ('make', 'run'),
                    'dict': {
                        'metavar': 'PROJECT',
                        'dest': 'workdir',
                        'help': 'path to the ArchAdept project (default: current directory)',
                        'type': Path,
                        'default': Path.cwd(),
                    },
                },
                {
                    'arg': '-i',
                    'top-level': False,
                    'commands': ('make', 'run'),
                    'dict': {
                        'metavar': 'IMAGE',
                        'dest': 'image',
                        'help': 'override Docker image repository (default: archadept/example-code-tools)',
                        'type': str,
                        'default': 'archadept/example-code-tools',
                    },
                },
                {
                    'arg': '-t',
                    'top-level': False,
                    'commands': ('make', 'run'),
                    'dict': {
                        'metavar': 'TAG',
                        'dest': 'tag',
                        'help': 'override Docker image tag (default: latest)',
                        'type': str,
                        'default': 'latest',
                    },
                },
                {
                    'arg': '-s',
                    'top-level': False,
                    'commands': ('run', ),
                    'dict': {
                        'dest': 'spawn_gdbserver',
                        'help': 'spawn GDB debug server and pause simulation at kernel entrypoint',
                        'action': 'store_true',
                    },
                },
                {
                    'arg': 'target',
                    'top-level': False,
                    'commands': ('make', ),
                    'dict': {
                        'metavar': 'TARGET',
                        'help': 'Makefile target from {all,clean,rebuild,dis,syms} (default: all)',
                        'type': str,
                        'choices': ('all', 'clean', 'rebuild', 'dis', 'syms', 'sects'),
                        'default': 'all',
                        'nargs': '?',
                    },
                },
                {
                    'arg': '-S',
                    'top-level': False,
                    'commands': ('make', ),
                    'dict': {
                        'dest': 'interleave',
                        'help': 'interleave source with disassembly (only available for \'dis\' target)',
                        'action': 'store_true',
                    },
                },
                {
                    'arg': '-D',
                    'top-level': False,
                    'commands': ('make', ),
                    'dict': {
                        'dest': 'disassemble_data',
                        'help': 'also disassemble any data found in code sections (only available for \'dis\' target)',
                        'action': 'store_true',
                    },
                },
                {
                    'arg': '-O',
                    'top-level': False,
                    'commands': ('make', ),
                    'dict': {
                        'dest': 'optimize',
                        'help': 'override project\'s default optimization level',
                        'type': int,
                        'choices': range(4),
                        'default': None,
                    },
                },
                {
                    'arg': 'container_id',
                    'top-level': False,
                    'commands': ('debug', ),
                    'dict': {
                        'metavar': 'CONTAINER',
                        'help': 'container in which the QEMU simulation is running, as given by `archadept run`',
                        'type': str,
                    },
                },
            ),
        }

        parser = argparse.ArgumentParser(prog='archadept')
        subparsers = parser.add_subparsers(help='commands', dest='command', required=True)

        # Tracks argument parsers and command-specific argument groups associated
        # with each command's help screen.
        m_subparsers = dict()
        m_groups = dict()
        for command in args_descr['commands']:
            subparser = subparsers.add_parser(command['command'], **command['dict'])
            m_subparsers[command['command']] = subparser
            if command['command'] not in m_groups:
                m_groups[command['command']] = dict()
            m_groups[command['command']]['flags'] = subparser.add_argument_group('command-specific options')
            m_groups[command['command']]['positionals'] = subparser.add_argument_group('command-specific positional arguments')

        # Programmatically add each arg to its associated commands.
        for arg in args_descr['args']:
            # We first need to build up a list of "target" parsers to which we'll
            # be adding this arg. This determines whether the arg appears for a
            # particular command's help screen, and in which section it appears.
            targets = []
            if 'top-level' in arg and arg['top-level']:
                # Common options section of all parsers.
                targets.append(parser)
                targets += [m_subparsers[command['command']] for command in args_descr['commands']]
            elif arg['arg'].startswith('-'):
                # Command-specific flags section of the specified commands.
                targets += [m_groups[command]['flags'] for command in arg['commands']]
            else:
                # Command-specific positionals section of the specified commands.
                targets += [m_groups[command]['positionals'] for command in arg['commands']]
            # Now simply add the arg to each target identified above.
            for target in targets:
                target.add_argument(arg['arg'], **arg['dict'])

        # Parse the args into this CommandLineArgs object.
        for k,v in vars(parser.parse_args()).items():
            if k == 'workdir' and not Path(v).is_absolute():
                v = Path(Path.cwd(), v)
            setattr(self, k, v)

        # Extra validation
        if self.command == 'make':
            if self.target != 'dis':
                if self.interleave:
                    parser.error('-S only available for Makefile target \'dis\'')
                if self.disassemble_data:
                    parser.error('-D only available for Makefile target \'dis\'')

def main_make(image:str, tag:str, workdir:Path, target:str, optimize:Optional[int]=None, interleave:bool=False, disassemble_data:bool=False) -> int:
    """ Main function for ``archadept make``.

    Parameters
    ----------
    image
        Docker image repository to use.
    tag
        Docker image tag to use.
    workdir
        Path to the ArchAdept example project.
    target
        Makefile target.
    optimize
        Compiler optimization level.
    interleave
        When ``target='dis'``, this enables interleaving of source code with
        the disassembly.
    disassemble_data
        When ``target='dis'``, this enables disassembling any data found in
        code sections.

    Returns
    -------
    Shell exit status of the underlying ``make`` invocation.
    """
    kwargs = {}
    if optimize is None:
        optimize = get_project_default_optimization_level(workdir)
    kwargs['OPTIMIZE'] = optimize
    if target == 'dis':
        if interleave:
            kwargs['INTERLEAVE'] = 1
        if disassemble_data:
            kwargs['DISASSEMBLE_DATA'] = 1
    result = DockerCLIWrapper().run(f'make {target}', image=image, tag=tag, host_workdir=workdir, env=kwargs)
    return result.returncode

def get_project_metadata(project:Path) -> Optional[dict]:
    """ Attempt to parse the project's `archadeptcli.toml` config file.

    Parameters
    ----------
    project
        Path to the project.
    """
    console = getConsole()
    try:
        toml_file = Path(project) / 'archadeptcli.toml'
        console.debug(f'trying to read project config file at \'{toml_file}\'...')
        with open(toml_file, 'rb') as f:
            d = tomllib.load(f)
    except OSError as e:
        console.debug(e)
        console.debug(f'Failed to open the project\'s \'archadeptcli.toml\' file.')
        return None
    except tomllib.TOMLDecodeError as e:
        console.debug(e)
        console.debug(f'Failed to parse the project\'s \'archadeptcli.toml\' file.')
        return None
    else:
        return d

def check_project_supports_run(project:Path) -> None:
    """ Determines whether an ArchAdept example project supports being run on
        a QEMU simulation of a Raspberry Pi 3b, printing a warning message if
        it seems like it does not.

    Parameters
    ----------
    project
        Path to the project.
    """
    console = getConsole()
    renderables = []
    metadata = get_project_metadata(project)
    if metadata is None:
        renderables.append(f'Unable to determine whether this project supports running on QEMU.')
    elif 'supports-run' not in metadata or not metadata['supports-run']:
        renderables.append(f'Project\'s \'archadeptcli.toml\' file does not advertise support for running on QEMU.')
    if renderables:
        renderables.append(f'Attempting to continue, but this may fail or not work as expected...')
        console.print(RichPanel.fit(RichGroup(*renderables), style='yellow'))

def get_project_default_optimization_level(project:Path) -> int:
    """ Get the default compilation optimization level for a project.
        This defaults to `-O1` if the project's `archadeptcli.toml`
        file cannot be found, cannot be parsed, or does not contain a
        valid `optimize` key.

    Parameters
    ----------
    project
        Path to the project.

    Returns
    -------
    The default compilation optimization level.
    """
    optimize = 1
    metadata = get_project_metadata(project)
    if metadata is not None and 'optimize' in metadata and isinstance(metadata['optimize'], int):
        optimize = metadata['optimize']
    return optimize

def print_qemu_help_message(container_id:str=None) -> None:
    """ Print the help message that is displayed when launching QEMU.

    Parameters
    ----------
    container_id
        If QEMU was instructed to spawn a GDB server then this is the ID of
        the Docker container in which QEMU is running, else ``None``.
    """
    renderables = []
    if container_id is not None:
        renderables.append('Simulation is paused waiting for debugger.\n' \
                               'Run this command in another window to attach the debugger:')
        debug_panel = RichPanel.fit(f'$ archadept debug {container_id}', style='blue')
        renderables.append(RichAlign.center(debug_panel))
    renderables.append('Press \'Ctrl-a\' followed by \'x\' to end the simulation.\n' \
                       'QEMU is now controlling this terminal window until the simulation ends...')
    getConsole().print(RichPanel.fit(RichGroup(*renderables), style='green'))

def main_run(image:str, tag:str, workdir:Path, spawn_gdbserver:bool) -> int:
    """ Main function for ``archadept run``.

    Parameters
    ----------
    image
        Docker image repository to use.
    tag
        Docker image tag to use.
    workdir
        Path to the ArchAdept example project.
    spawn_gdbserver
        Whether to spawn a GDB server and pause simulation at kernel entrypoint.

    Returns
    -------
    Shell exit status of the underlying QEMU simulation.
    """
    console = getConsole()
    docker = DockerCLIWrapper()
    returncode = main_make(image, tag, workdir, 'rebuild', None)
    if returncode != 0:
        return returncode
    check_project_supports_run(workdir)
    qemu_cmdline = f'qemu-system-aarch64 -M raspi3b -nographic -kernel build/out.elf'
    if spawn_gdbserver:
        qemu_cmdline += ' -s -S'
    else:
        print_qemu_help_message()
    result = docker.run(qemu_cmdline, detached=spawn_gdbserver, image=image, tag=tag, host_workdir=workdir)
    if not spawn_gdbserver:
        return result.returncode
    if result.returncode != 0:
        docker.error_cli_result(result)
        raise SimulationError('failed to start QEMU simulation')
    container_id = result.output
    if len(container_id) > 16:
        container_id = container_id[:16]
    print_qemu_help_message(container_id=container_id)
    return docker.attach(container_id).returncode

def main_debug(container_id:str) -> int:
    """ Main function for ``archadept debug``.

    Parameters
    ----------
    container_id
        ID of the container in which the QEMU simulation is running.

    Returns
    -------
    Shell exit status of the underlying GDB invocation.
    """
    docker = DockerCLIWrapper()
    gdb_command = 'aarch64-none-elf-gdb -q -ex \'target remote localhost:1234\' -ex \'set prompt \\n(gdb) \' build/out.elf'
    if Path.exists(docker.get_project_dir(container_id) / 'gdb-commands.py'):
        gdb_command += ' -x \'gdb-commands.py\''
    return docker.exec(container_id, gdb_command).returncode

def main_prune() -> int:
    """ Main function for ``archadept prune``.

    Returns
    -------
    Always returns 0; any issues will have raised an ``ArchAdeptError``.
    """
    DockerCLIWrapper().prune()
    return 0

def main():
    """ Main entrypoint function when invoked from the command line. """
    args = CommandLineArgs()
    archadeptcli.console.init(debug=args.debug)
    try:
        if args.command == 'make':
            return main_make(args.image, args.tag, args.workdir, args.target, optimize=args.optimize,
                             interleave=args.interleave, disassemble_data=args.disassemble_data)
        elif args.command == 'run':
            return main_run(args.image, args.tag, args.workdir, args.spawn_gdbserver)
        elif args.command == 'debug':
            return main_debug(args.container_id)
        elif args.command == 'prune':
            return main_prune()
        else:
            raise InternalError(f'unimplemented function: main_{args.command}()')
    except ArchAdeptError as e:
        if args.debug:
            raise e
        else:
            getConsole().print(e)
            return 1
    except Exception as e:
        raise UngracefulExit('crashed due to uncaught exception') from e

