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
import json
from pathlib import Path
from typing import Any, Optional

# Third-party deps
import rich.traceback
rich.traceback.install(show_locals=True, suppress=[rich])

# Local deps
import archadeptcli
from archadeptcli.console import getConsole, RichAlign, RichGroup, RichPanel, Color
from archadeptcli.docker import DockerCLIWrapper
from archadeptcli.exceptions import *
from archadeptcli.diagram import main_diagram

ARCHADEPTCLI_BASE_TAG = '1.2.2'
""" Current base tag of the archadeptcli repository. """




class CommandLineArgs():
    """ Class representing the arguments parsed from the command line. """

    def __init__(self):
        """ Parse command line arguments. """

        field_help = 'The ``--field`` option may be used to manually describe ' \
                     'fields in the form "{name}\\[hi{:lo}\\]{=value}". For example, ' \
                     '"sf[31]" describes a one-bit field named "sf" at bit ' \
                     'position 31, while "Rn[9:5]=0x5" describes a 5-bit wide ' \
                     'field named "Rn" spanning bit positions 9 to 5 inclusive ' \
                     'and with value 0x5. The name is also optional, so "[31]" ' \
                     'describes an anonymous bit at position 31 with no value, ' \
                     'while "[31:30]=0x3" describes an anonymous field spanning ' \
                     'bits 31 to 30 inclusive with value 0x3.'

        # Data-driven description which we use at runtime to programmatically
        # generate the various argument parsers. This also lets us share flags
        # and arguments between commands without duplicated code/logic.
        args_descr = {
            'groups': (
                {
                    'name': 'project',
                    'dict': {
                        'aliases': ('proj', 'p'),
                        'help': 'build, run, disassemble, and debug bare metal projects',
                    },
                },
                {
                    'name': 'utility',
                    'dict': {
                        'aliases': ('util', 'u'),
                        'help': 'utilities such as generating diagrams of instruction opcodes and system registers',
                    },
                },
            ),
            'commands': (
                {
                    'command': 'make',
                    'group': 'project',
                    'dict': {
                        'help': 'invoke project Makefile',
                        'description': 'Invokes an ArchAdept example project Makefile.',
                    },
                },
                {
                    'command': 'run',
                    'group': 'project',
                    'dict': {
                        'help': 'run project on simulated hardware',
                        'description': 'Runs an ArchAdept example project on a simulated Raspberry Pi 3b.',
                    },
                },
                {
                    'command': 'debug',
                    'group': 'project',
                    'dict': {
                        'help': 'attach debugger to live simulation',
                        'description': 'Attaches an LLDB debug session to a live QEMU simulation started by `archadept run -s`.',
                    },
                },
                {
                    'command': 'pull',
                    'group': 'project',
                    'dict': {
                        'help': 'pull the latest Docker image',
                        'description': 'Pulls the latest ArchAdept CLI backend Docker image from DockerHub.',
                    },
                },
                {
                    'command': 'prune',
                    'group': 'project',
                    'dict': {
                        'help': 'clean up any lingering Docker containers',
                        'description': 'Cleans up any lingering Docker containers from previous ArchAdept CLI invocations.',
                    },
                },
                {
                    'command': 'opcode',
                    'group': 'utility',
                    'dict': {
                        'help': 'generate diagrams of instruction opcode encodings',
                        'description': 'Generates diagrams of instruction opcode encodings.',
                        'aliases': ('op', 'o'),
                        'epilog': field_help,
                    },
                },
                {
                    'command': 'register',
                    'group': 'utility',
                    'dict': {
                        'help': 'generate diagrams of system registers',
                        'description': 'Generates diagrams of system registers.',
                        'aliases': ('reg', 'r'),
                        'epilog': field_help,
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
                    'arg': '-d',
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
                    'commands': ('make', 'run', 'pull', ),
                    'dict': {
                        'metavar': 'IMAGE',
                        'dest': 'image',
                        'help': 'override Docker image repository (default: archadept/archadeptcli-backend)',
                        'type': str,
                        'default': 'archadept/archadeptcli-backend',
                    },
                },
                {
                    'arg': '-t',
                    'top-level': False,
                    'commands': ('make', 'run', 'pull', ),
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
                {
                    'arg': '--field',
                    'top-level': False,
                    'commands': ('opcode', ),
                    'dict': {
                        'metavar': 'F',
                        'type': str,
                        'nargs': '+',
                        'help': 'manually describe an instruction opcode (see below)',
                        'default': None,
                    },
                },
                {
                    'arg': '--field',
                    'top-level': False,
                    'commands': ('register', ),
                    'dict': {
                        'metavar': 'F',
                        'type': str,
                        'nargs': '+',
                        'help': 'manually describe a system register (see below)',
                        'default': None,
                    },
                },
                {
                    'arg': 'NAME',
                    'top-level': False,
                    'commands': ('opcode', ),
                    'dict': {
                        'help': 'name of the instruction (example: "add")',
                        'type': str,
                        'default': None,
                        'nargs': '*',
                    },
                },
                {
                    'arg': 'NAME',
                    'top-level': False,
                    'commands': ('register', ),
                    'dict': {
                        'help': 'name of the system register (example: "hcr_el2")',
                        'type': str,
                        'default': None,
                        'nargs': '*',
                    },
                },
                {
                    'arg': '-s',
                    'top-level': False,
                    'commands': ('opcode', 'register', ),
                    'dict': {
                        'help': 'how many bits wide each section should be (default: 32)',
                        'type': int,
                        'choices': (8, 16, 32, 64),
                        'default': 32,
                    },
                },
                {
                    'arg': '--ascii',
                    'top-level': False,
                    'commands': ('opcode', 'register'),
                    'dict': {
                        'help': 'dump rendered ASCII diagram to stdout',
                        'action': 'store_true',
                        'default': False,
                    },
                },
                {
                    'arg': '--bow',
                    'top-level': False,
                    'commands': ('opcode', 'register'),
                    'dict': {
                        'help': 'generate black-on-white PNG image',
                        'action': 'store_true',
                        'default': False,
                    },
                },
                {
                    'arg': '--bot',
                    'top-level': False,
                    'commands': ('opcode', 'register'),
                    'dict': {
                        'help': 'generate black-on-transparent PNG image',
                        'action': 'store_true',
                        'default': False,
                    },
                },
                {
                    'arg': '--wob',
                    'top-level': False,
                    'commands': ('opcode', 'register'),
                    'dict': {
                        'help': 'generate white-on-black PNG image',
                        'action': 'store_true',
                        'default': False,
                    },
                },
                {
                    'arg': '--wot',
                    'top-level': False,
                    'commands': ('opcode', 'register'),
                    'dict': {
                        'help': 'generate white-on-transparent PNG image',
                        'action': 'store_true',
                        'default': False,
                    },
                },
                {
                    'arg': '--all',
                    'top-level': False,
                    'commands': ('opcode', 'register'),
                    'dict': {
                        'help': 'equivalent to `--ascii --bow --bot --wob --wot`',
                        'action': 'store_true',
                        'default': False,
                    },
                },
                {
                    'arg': '--font',
                    'top-level': False,
                    'commands': ('opcode', 'register'),
                    'dict': {
                        'metavar': 'PATH',
                        'help': 'path to TTF font to use in PNG images (default: bundled FiraCodeNerdFont-Regular.tff)',
                        'type': Path,
                        'default': None,
                    },
                },
                {
                    'arg': '--prefix',
                    'top-level': False,
                    'commands': ('opcode', ),
                    'dict': {
                        'metavar': 'NAME',
                        'help': 'PNG image file name prefix when manually specifying fields (example: "add-w0-w1-w0")',
                        'type': str,
                        'default': None,
                    },
                },
                {
                    'arg': '--prefix',
                    'top-level': False,
                    'commands': ('register', ),
                    'dict': {
                        'metavar': 'NAME',
                        'help': 'PNG image file name prefix when manually specifying fields (example: "hcr_el2")',
                        'type': str,
                        'default': None,
                    },
                },
                {
                    'arg': '--value',
                    'top-level': False,
                    'commands': ('register', ),
                    'dict': {
                        'help': 'overlay the given value over the entire system register',
                        'metavar': 'NUM',
                        'type': str,
                        'default': None,
                    },
                },
                {
                    'arg': '--value',
                    'top-level': False,
                    'commands': ('opcode', ),
                    'dict': {
                        'help': 'overlay the given value over the entire instruction opcode encoding',
                        'metavar': 'NUM',
                        'type': str,
                        'default': None,
                    },
                },
            ),
        }

        # Create the top-level argument parser, and separate subparsers for
        # each of the command groups e.g. 'project' and 'utility'.
        top_level_parser = argparse.ArgumentParser(prog='archadept')
        top_level_subparser = top_level_parser.add_subparsers(required=True, dest='command_as_provided')
        subparsers = {}
        for group in args_descr['groups']:
            subparser = top_level_subparser.add_parser(group['name'], **group['dict'])
            subparser.set_defaults(command=group['name'])
            subparsers[group['name']] = subparser.add_subparsers(dest='subcommand_as_provided')

        # Build up two dicts tracking the argument parsers and command-specific
        # argument groups associated with each command's individual help screen.
        m_subparsers = dict()
        m_groups = dict()
        for command in args_descr['commands']:
            parent = subparsers[command['group']]
            m_subparsers[command['command']] = parent.add_parser(command['command'], **command['dict'])
            m_subparsers[command['command']].set_defaults(subcommand=command['command'])
            if command['command'] not in m_groups:
                m_groups[command['command']] = dict()
            m_groups[command['command']]['flags'] = m_subparsers[command['command']].add_argument_group('command-specific options')
            m_groups[command['command']]['positionals'] = m_subparsers[command['command']].add_argument_group('command-specific positional arguments')

        # Programmatically add each arg to its associated commands.
        for arg in args_descr['args']:
            # We first need to build up a list of "target" parsers to which we'll
            # be adding this arg. This determines whether the arg appears for a
            # particular command's help screen, and in which section it appears.
            targets = []
            if 'top-level' in arg and arg['top-level']:
                # Common options section of all parsers.
                targets.append(top_level_parser)
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
        for k,v in vars(top_level_parser.parse_args()).items():
            if k == 'workdir' and not Path(v).is_absolute():
                v = Path(Path.cwd(), v)
            setattr(self, k, v)

        # Extra validation
        if self.subcommand == 'make':
            if self.target != 'dis':
                if self.interleave:
                    top_level_parser.error('-S only available for Makefile target \'dis\'')
        if self.subcommand in ('opcode', 'register'):
            if self.NAME and self.field:
                a_type_name = 'an instruction' if self.subcommand == 'opcode' else 'a register'
                top_level_parser.error(f'manually specifying fields using ``--field`` is mutually exclusive with specifying {a_type_name} name')
            elif self.NAME is not None:
                if len(self.NAME) > 1:
                    type_name = 'instruction' if self.subcommand == 'opcode' else 'register'
                    top_level_parser.error(f'expected exactly one {type_name} name')
                elif len(self.NAME) == 1:
                    self.NAME = self.NAME[0]

def main_make(image:str, tag:str, workdir:Path, target:str, optimize:Optional[int]=None, interleave:bool=False) -> int:
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
    result = DockerCLIWrapper().run(f'make {target}', image=image, tag=tag, host_workdir=workdir, env=kwargs)
    return result.returncode

def get_project_metadata(project:Path) -> Optional[dict]:
    """ Attempt to parse the project's `archadeptcli.json` config file.

    Parameters
    ----------
    project
        Path to the project.
    """
    console = getConsole()
    try:
        config_file = Path(project) / 'archadeptcli.json'
        console.debug(f'trying to read project config file at \'{config_file}\'...')
        with open(config_file, 'r') as f:
            ret = json.load(f)
    except OSError as e:
        console.debug(e)
        console.debug(f'Failed to open the project\'s \'archadeptcli.json\' file.')
        return None
    except json.decoder.JSONDecodeError as e:
        console.debug(e)
        console.debug(f'Failed to parse the project\'s \'archadeptcli.json\' file.')
        return None
    else:
        return ret

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
    metadata = get_project_metadata(project)
    if metadata is None:
        ProjectRunSupportUnknown(f'Unable to determine whether this project supports being run on QEMU.')
    elif 'supports-run' not in metadata or not metadata['supports-run']:
        ProjectDoesNotSupportRun(f'Project config file states it does not support being run on QEMU.')

def get_project_default_optimization_level(project:Path) -> int:
    """ Get the default compilation optimization level for a project.
        This defaults to `-O1` if the project's `archadeptcli.json`
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
        debug_panel = RichPanel.fit(f'$ archadept debug {container_id}', style=Color.EXTRA)
        renderables.append(RichAlign.center(debug_panel))
    renderables.append('Press \'Ctrl-a\' followed by \'x\' to end the simulation.\n' \
                       'QEMU is now controlling this terminal window until the simulation ends...')
    getConsole().print(RichPanel.fit(RichGroup(*renderables), style=Color.INFO))

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
    Shell exit status of the underlying LLDB invocation.
    """
    docker = DockerCLIWrapper()
    lldb_command = 'lldb -Q --one-line "gdb-remote localhost:1234" build/out.elf'
    return docker.exec(container_id, lldb_command).returncode

def main_pull(image:str, tag:str) -> int:
    """ Main function for ``archadept pull``.

    Parameters
    ----------
    image
        Docker image repository to use.
    tag
        Docker image tag to use.

    Returns
    -------
    Shell exit status of the underlying ``docker pull` invocation.
    """
    return DockerCLIWrapper().pull(image, tag)

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
        # We currently don't have identically named subcommands across the two
        # top-level 'project' and 'utility' commands, so we only need to key
        # off of the subcommand here.
        if args.subcommand == 'make':
            return main_make(args.image, args.tag, args.workdir, args.target, optimize=args.optimize, interleave=args.interleave)
        elif args.subcommand == 'run':
            return main_run(args.image, args.tag, args.workdir, args.spawn_gdbserver)
        elif args.subcommand == 'debug':
            return main_debug(args.container_id)
        elif args.subcommand == 'pull':
            return main_pull(args.image, args.tag)
        elif args.subcommand == 'prune':
            return main_prune()
        elif args.subcommand in ('opcode', 'register'):
            do_ascii = args.ascii or args.all
            do_bow = args.bow or args.all
            do_bot = args.bot or args.all
            do_wob = args.wob or args.all
            do_wot = args.wot or args.all
            if not any((do_ascii, do_bow, do_bot, do_wob, do_wot)):
                do_ascii = True
            fields = getattr(args, 'field', None)
            return main_diagram(args.subcommand == 'opcode', args.NAME, fields,
                                args.s, do_ascii, do_bow, do_bot, do_wob, do_wot,
                                args.font, args.prefix, args.value)
        else:
            raise InternalError(f'unimplemented function: main_{args.subcommand}()')
    except ArchAdeptError as e:
        e.render()
        if args.debug:
            raise e
        else:
            return 1
    except Exception as e:
        raise UngracefulExit('crashed due to uncaught exception') from e

