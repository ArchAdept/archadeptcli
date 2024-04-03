"""
Copyright © 2024, ARCHADEPT LTD. All Rights Reserved.

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
import importlib.resources
import json
import re
from pathlib import Path
from typing import Optional, Union

# Third-party deps
import fuzzywuzzy
from fuzzywuzzy import process

# Local deps
from archadeptcli.console import getConsole, RichAlign, RichGroup, RichPanel, Color
from archadeptcli.exceptions import *

gDEFAULT_FONT = 'FiraCodeNerdFont-Regular'

class Field():
    """ Class representing a single field in a register layout or
        instruction encoding. """

    def __init__(self, name:str, hi:Union[int, str], lo:Union[int, str],
                 value:Optional[Union[int, str]]=None, hide_hi:bool=False, hide_lo:bool=False):
        """ Constructor.

        Parameters
        ==========
        name
            Name of this field (example: TWEDEL)
        hi
            High bit position of the field; must be in range ``[0..63]``
            inclusive and greater than or equal to ``lo``.
        lo
            Low bit position of the field; must be in range ``[0..63]``
            inclusive and less than or equal to ``hi``.
        value
            Optional value which will be overlaid over this field in the
            rendered diagram.
        hide_hi
            Whether to hide the high bit position of this field; used
            for the far-left field of the lower render when that field
            spans both renders.
        hide_lo
            Whether to hide the low bit position of this field; used
            for the far-right field of the upper render when that field
            spans both renders.
        """
        if isinstance(hi, str):
            hi = int(hi)
        if hi < 0 or hi > 63:
            raise ValueError(f'new field "{name}": {hi=}, must be in range [0..63] inclusive')
        if isinstance(lo, str):
            lo = int(lo)
        if lo < 0 or lo > 63:
            raise ValueError(f'new field "{name}": {lo=}, must be in range [0..63] inclusive')
        if hi < lo:
            raise ValueError(f'new field "{name}": {hi=}, must be >= {lo=}')
        self.hi = hi
        self.lo = lo
        self.pad = (5 * (hi - lo)) + 4
        if value is not None:
            try:
                if value.startswith('0x'):
                    value = int(value, 16)
                elif value.startswith('0b'):
                    value = int(value, 2)
                else:
                    value = int(value)
            except ValueError:
                if not all((c in ('0', '1', 'X') for c in value)):
                    raise ValueError(f'new field "{name}": {value=}, failed to parse as an integer')
            else:
                value = f'{value:b}'
            num_bits = (hi - lo) + 1
            if len(value) > num_bits:
                raise ValueError(f'new field "{name}": binary representation "{value}" does not fit in {num_bits}-bit wide field')
            value = ('0' * (num_bits - len(value))) + value
            value = ' ' + '    '.join(c for c in value)
        if name is None and value is not None:
            name = value
            value = None
        if value is None and name is not None and all((c in ('0', '1') for c in name)):
            name = ' ' + '    '.join(c for c in name)
        if name is None and value is None:
            name = ''
        self.name = name
        self.value = value
        self.drop_h = -1
        self.drop_v = -1
        self.hide_hi = hide_hi
        self.hide_lo = hide_lo

class Layout():
    """ Class representing an entire register layout or instruction opcode
        encoding, which can be rendered to an ASCII string diagram. """

    def __init__(self) -> None:
        """ Constructor. """
        self.fields = []

    def field(self, *args):
        """ Add a new field to this layout.

        Parameters
        ==========
        Same as for ``Field`` class constructor.
        """
        (name, hi, lo, value) = args
        new = Field(name, hi, lo, value=value)
        for old in self.fields:
            if new.hi <= old.lo and new.lo >= old.hi:
                raise ValueError(f'new field "{name}" [{hi}:{lo}] overlaps old field "{old.name}" [{old.hi}:{old.lo}]')
        self.fields.append(new)

    def render(self, split:int) -> list[str]:
        """ Render this ``Layout`` to an ASCII string diagram.

        Parameters
        ==========
        split
            How many bits wide each section of the render should be.
            Supported values: 8, 16, 32.

        Returns
        =======
        List of strings representing each line of the rendered ASCII diagram.
        """

        def render2(fields:list[Field]) -> str:
            """ Internal implementation of ``render()``, allowing us to
                separately render the upper and lower halves of a register.

            Parameters
            ==========
            fields
                List of ``Field``s to render.

            Returns
            =======
            The ``Field``s rendered as an ASCII diagram.
            """

            def first_last(fields, field) -> tuple[bool, bool]:
                """ Helper function to determine whether the given ``Field``
                    is the the far-left or far-right field of this render.

                Parameters
                ==========
                field
                    The field to check.

                Returns
                =======
                Tuple of the form ``[first:bool, last:bool]``.
                """
                index = list(fields).index(field)
                first, last = (index == 0), (index == len(fields) - 1)
                return (first, last)

            lines = []

            # Top line
            line = 30 * ' '
            for field in fields:
                first, last = first_last(fields, field)
                line += '┌' if first else '┬'
                line += field.pad * '─'
                if last:
                    line += '┐'
            lines.append(line)

            # Field bit positions
            line = ''
            line = 30 * ' '
            for field in fields:
                first, last = first_last(fields, field)
                line += '│'
                if field.hi > field.lo:
                    line += f' {field.hi:>2d}' if not field.hide_hi else '   '
                    line += (field.pad - 6) * ' '
                    line += f'{field.lo:>2d} ' if not field.hide_lo else '   '
                else:
                    line += f' {field.hi:>2d} '
                if last:
                    line += '│'
            lines.append(line)

            # Middle line
            line = ''
            line = 30 * ' '
            for field in fields:
                first, last = first_last(fields, field)
                line += '├' if first else '┼'
                line += field.pad * '─'
                if last:
                    line += '┤'
            lines.append(line)

            # Field name
            line = ''
            line = 30 * ' '
            for field in fields:
                _, last = first_last(fields, field)
                line += '│'
                text = field.value if field.value is not None else field.name
                if len(text) <= field.pad - 2:
                    line += f'{text:^{field.pad}s}'
                else:
                    line += field.pad * ' '
                if last:
                    line += '│'
            lines.append(line)

            # Bottom line
            line = 30 * ' '
            max_drop_h = 0
            for field in fields:
                first, last = first_last(fields, field)
                line += '└' if first else '┴'
                field.drop_h = len(line) + 1 + field.pad//2
                max_drop_h = max(field.drop_h + len(field.name) + 4, max_drop_h)
                if field.value is None and len(field.name) <= field.pad - 2:
                    line += field.pad * '─'
                else:
                    if field.pad % 2 == 0:
                        line += f'{(field.pad//2)*"─"}┬{((field.pad//2)-1)*"─"}'
                    else:
                        line += f'{field.pad//2*"─"}┬{((field.pad//2))*"─"}'
                if last:
                    line += '┘'
            lines.append(line)

            # Search for consecutive "runs" of fields whose names did not
            # fit in the allocated screen space, or who had overlaid values.
            run, runs = [], []
            for field in fields:
                if field.value is None and len(field.name) <= field.pad - 2:
                    if run:
                        runs.append(run)
                        run = []
                else:
                    run.append(field)
            if run:
                runs.append(run)

            # Now determine how far down each arrow will go, and whether
            # the field's name will go to the left or right of the arrow.
            max_drop_v = 0
            for run in runs:
                drop_v = 0
                last_h = -1
                flipped = False
                for idx, field in enumerate(run):
                    if idx <= len(run) // 2:
                        # Name goes to the left of the arrow
                        field.direction = -1
                        # Will we be clobbering over the previous field?
                        # On this side of the run, that means that our
                        # name being rendered to the left of the current
                        # drop_h would overwrite any part of the previous
                        # field's drop_h.
                        h = field.drop_h - len(field.name) - 4
                        clobber = h <= last_h
                        last_h = field.drop_h
                    else:
                        # Name goes to the right of the arrow
                        field.direction = +1
                        # Will we be clobbering over the previous field?
                        if not flipped:
                            # If this is the iteration where we're flipping
                            # direction then no, we cannot be clobbering the
                            # previous field. From now on, last_h is calculated
                            # as the current field's drop_h *PLUS* the space
                            # required to render it to the right of the arrow,
                            # rather than *MINUS* the space required to render
                            # it to the left of the arrow.
                            clobber = False
                            flipped = True
                        else:
                            clobber = field.drop_h <= last_h
                        last_h = field.drop_h + len(field.name) + 4
                    # OK, if we're clobbering then we want to either drop down
                    # a line if we're rendering the first half of a run, or
                    # climb up a line if we're rendering the second half of a
                    # run.
                    if clobber:
                        drop_v -= field.direction
                    field.drop_v = drop_v
                    max_drop_v = max(drop_v, max_drop_v)

            # Finally, render the arrows and names
            for i in range(max_drop_v+1):
                line = max_drop_h * ' '
                for field in fields:
                    if i < field.drop_v:
                        line = line[:field.drop_h-1] + '│' + line[field.drop_h:]
                    elif i == field.drop_v:
                        if field.direction < 0:
                            line = line[:field.drop_h - len(field.name) - 4] + f'{field.name} ◄─┘' + line[field.drop_h:]
                        else:
                            line = line[:field.drop_h-1] + f'└─► {field.name}' + line[field.drop_h + len(field.name) + 4:]
                lines.append(line)

            # Done!
            return lines

        field_set = []
        field_sets = []
        remaining_fields = self.fields
        boundaries = list(reversed(list(range(0, 63, split))[1:]))
        while len(boundaries) > 1 and boundaries[0] >= self.fields[0].hi + 1:
            boundaries = boundaries[1:]
        b = 0
        while remaining_fields:
            field = remaining_fields[0]
            if b < len(boundaries) and field.lo == boundaries[b]:
                # This ``Field`` starts at the boundary bit, so we can
                # simply cut the list of ``Field``s at this point.
                field_set += [field]
                field_sets += [field_set]
                field_set = []
                remaining_fields = remaining_fields[1:]
                b += 1
            elif b < len(boundaries) and field.hi >= boundaries[b] and field.lo < boundaries[b]:
                # This ``Field`` spans the boundary; let's create two
                # dummy ``Field``s to separately render at the end of
                # the current section and at the beginning of the next
                # section.
                dummy_hi = Field(field.name + ' (cont.)', field.hi, boundaries[b], hide_lo=True)
                dummy_lo = Field(field.name, boundaries[b]-1, field.lo, hide_hi=True) 
                field_set += [dummy_hi]
                field_sets += [field_set]
                field_set = []
                remaining_fields = [dummy_lo] + remaining_fields[1:]
                b += 1
            else:
                field_set += [field]
                remaining_fields = remaining_fields[1:]
        if field_set:
            field_sets += [field_set]

        # Render the register(s) or instruction opcode encoding. While
        # we're here we also determine where we'll need to insert
        # continuation markers later.
        lines = []
        to_prefix, to_suffix = set(), set()
        for idx, fs in enumerate(field_sets):
            is_first = idx == 0
            is_last = idx == len(field_sets) - 1
            spread = list(range(len(lines)+1, len(lines)+4))
            if is_first and not is_last:
                [to_suffix.add(s) for s in spread]
            elif is_last and not is_first:
                [to_prefix.add(s) for s in spread]
            elif not is_first and not is_last:
                [to_prefix.add(s) for s in spread]
                [to_suffix.add(s) for s in spread]
            lines += render2(fs)
            lines.append('\n')

        # Strip leading and trailing whitespace.
        min_start = 999
        for line in lines:
            if line.strip():
                start = len(line) - len(line.lstrip())
                min_start = min(start, min_start)
        for i in range(len(lines)):
            lines[i] = lines[i][min_start:].rstrip()

        # And now insert the continuation markers
        for idx in range(len(lines)):
            spaces = len(lines[idx]) - len(lines[idx].lstrip()) + 1
            lines[idx] = f'{" "*spaces}{":" if idx in to_prefix else " "}{lines[idx].lstrip()}'
            lines[idx] = f'{lines[idx]}{":" if idx in to_suffix else ""}'

        #Done!
        return lines

def prompt(query:str, choices:list[str]) -> Optional[str]:
    for idx, choice in enumerate(reversed(choices)):
        suffix = '' if idx < len(choices)-1 else ' <-- this is the closest match'
        print(f' {len(choices)-idx:>3d}) {choice}{suffix}')
    selection = input(f'\n{query} > ')
    error_message = f'Invalid choice \'{{}}\', expected an integer in the range [1..{len(choices)}] inclusive.'
    try:
        selection = int(selection) - 1
    except ValueError:
        print(error_message.format(selection))
        return None
    if selection < 0 or selection >= len(choices):
        print(error_message.format(selection))
        return None
    return choices[selection]

def prompt_yesno(question:str) -> bool:
    choice = input(f'{question} (Y/n) > ').strip()
    return not choice or all((c.lower() == 'y' for c in choice))

def main_diagram(opcode_not_register:bool, name:str, fields:list[str], split:int,
                 do_ascii:bool, do_bow:bool, do_bot:bool, do_wob:bool, do_wot:bool,
                 font:Path, prefix:str, value:str) -> int:

    # Create an empty ``Layout`` and determine the overlay value, if applicable.
    console = getConsole()
    layout = Layout()
    full_value = None
    if value is not None:
        try:
            if value.startswith('0x'):
                full_value = int(value, 16)
            elif value.startswith('0b'):
                full_value = int(value, 2)
            else:
                full_value = int(value)
        except ValueError:
            raise BadDiagramValue(f'failed to parse \'{value}\'')
        else:
            full_value = f'{full_value:b}'
            full_value = ((64 - len(full_value)) * '0') + full_value
            full_value = ''.join(reversed(full_value))
            console.debug(f'{full_value=}')

    def add_field(name, hi, lo, value) -> None:
        """ Helper function to add a field to the layout.

        Parameters
        ==========
        See ``Field`` class.
        """
        nonlocal layout
        nonlocal full_value
        if lo is None:
            lo = hi
        if value is None and full_value is not None:
            value = ''.join(reversed(full_value[int(lo):int(hi)+1]))
            # Prevent callout arrows being placed on this field if it has
            # a fixed value.
            if value == name:
                value = None
            elif value is not None:
                value = f'0b{value}'
        layout.field(name, hi, lo, value)

    if fields:
        # User is manually specifying fields via ``--field``; parse them out.
        regex = r'^(?:([^\[]+))?\[([0-9]+)(?::(\d+))?\](?:=(.*))?'
        for field in fields:
            match = re.match(regex, field)
            if match is None:
                raise BadDiagramField(f'invalid format: \'{field}\'')
            (name, hi, lo, value) = match.groups()
            add_field(name, hi, lo, value)
    else:
        # If the user isn't manually specifying fields then we'll need to lookup
        # the instruction opcode / system register layout in the corresponding
        # data file. These files are parsed from the Arm Architecture XML using
        # the scripts in the top-level `tools/` directory.
        type_name = 'instruction' if opcode_not_register else 'register'
        json_file = importlib.resources.files('archadeptcli.static').joinpath(f'{type_name}s.json')
        console.debug(f'opening data file at: {json_file}')
        with open(json_file, 'r') as f:
            d = json.load(f)
        choices = sorted(list(d.keys()))
        console.debug(f'loaded {len(choices)} {type_name}(s)')
        # The user may pass '?' to dump a list of all known instructions/registers.
        if name == '?':
            if prompt_yesno(f'Show all {len(choices)} results?'):
                print('\n'.join(choices))
            return 0
        # Use ``FuzzyWuzzy`` to calculate the Levenshtein distances from the
        # name provided by the user to all known names, then filter out anything
        # with a similarity score less than 75.
        console.debug(f'performing fuzzy search...')
        scores = process.extract(name, choices, limit=None)
        console.debug(f'got {len(scores)} raw results')
        scores = list(filter(lambda t: t[1] >= 75, scores))
        console.debug(f'filtered this down to {len(scores)} with a similarity score >= 75')
        chosen = None
        if len(scores) >= 1 and scores[0][0].strip() == name.strip():
            # Exact match
            chosen = scores[0][0]
            console.debug(f'exact match: {name}')
        elif len(scores) > 1:
            # Ambiguous match, ask the user to choose; these will already be
            # sorted in descending order of similarity score so we can simply
            # plug out the strings.
            console.debug(f'fuzzy search got {len(scores)} results, prompting user to clarify...')
            choices = list((score[0] for score in scores))
            chosen = prompt(f'Ambiguous {type_name} \'{name}\', please select from the list', choices)
        if chosen is not None:
            name = chosen
            fields = d[chosen]
        else:
            console.debug(f'no valid choice made/available, bailing out')
            return 1
        for field in fields:
            add_field(field['name'], field['hi'], field['lo'], field['value'])

    # Render the ASCII art diagram
    lines = layout.render(split)
    text = '\n'.join(lines)
    if ascii or all:
        print(text)

    # Has the user requested we generate any images?
    if not any((do_bow, do_bot, do_wob, do_wot)):
        return
    else:
        # This is slow, hence only importing it if we need it
        from PIL import Image, ImageDraw, ImageFont

    def load_font(font_path:Optional[Path]) -> Optional[ImageFont]:
        """ Helper function to load a font.

        Parameters
        ==========
        font_path
            Path to the font to load, or ``None`` to default to using
            ``FiraCodeNerdFont-Regular``, which is bundled up with the
            ``archadeptcli`` package installation.

        Returns
        =======
        The loaded ``ImageFont`` on success, else ``None``.
        """
        if font_path is None:
            font_sub_path = Path(gDEFAULT_FONT) / f'{gDEFAULT_FONT}.ttf'
            font_path = importlib.resources.files('archadeptcli.static').joinpath(font_sub_path)
        try:
            font = ImageFont.truetype(font_path, 40)
        except OSError as e:
            if 'cannot open resource' in str(e):
                return None
            else:
                raise e
        else:
            return font

    # Load the font that we'll be using to generate PNG images
    font = load_font(font)
    if font is None and font is not None:
        FontNotFound(f'error: unable to open font file "{font_path}", defaulting to "{gDEFAULT_FONT}"')
        font = load_font(None)
    if font is None:
        InternalError(f'failed to load any font, not even "{gDEFAULT_FONT}"!')

    # Identify the longest line in the textual output
    ml_idx, ml = (-1, -1)
    for idx, line in enumerate(lines):
        if len(line) > ml:
            ml = len(line)
            ml_idx = idx

    # Now use that to determine the dimensions of the image. To do this,
    # we first get the bounding box around a bitmask of the longest line,
    # which is of the form ``(x0, y0, x1, y1)``. Here ``x0`` will always
    # be ``0``, so the width of the image is simply ``x1``. For the height
    # of the image, again ``y0`` will always be ``0``, however we cannot
    # simply take ``y1``; we need to factor in the descent of the chosen
    # font (how far down below the line goes the longest character), and
    # also multiply the result by the total number of lines.
    (_, _, x1, y1) = font.getmask(lines[ml_idx]).getbbox()
    _, desc = font.getmetrics()
    w, h = x1, (y1 + desc) * len(lines)

    # Create a new dummy image of the correct size and draw the text on it
    image = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), text, font=font, fill='black')

    # Now pull out just the alpha channel and get the bounding box around
    # this channel. We use this for two purposes: firstly, to crop the
    # image above to strictly those pixels that have actually been drawn
    # to, and then later to reposition our final images.
    alpha = image.getchannel('A')
    alpha_bbox = alpha.getbbox()
    (ax0, ay0, _, _) = alpha_bbox

    # So, first, crop the image to only the pixels that have been drawn to,
    # and determine the size of the final output images.
    cropped = image.crop(alpha_bbox)
    (cx0, cy0, cx1, cy1) = cropped.getbbox()
    padding = 6
    w, h = (cx1-cx0)+2*padding, (cy1-cy0)+2*padding

    combinations = (
        (do_bow, 'black', 'white'),
        (do_bot, 'black', 'transparent'),
        (do_wob, 'white', 'black'),
        (do_wot, 'white', 'transparent'))

    # Now create brand new images with the chosen colours
    for (requested, foreground, background) in combinations:
        if not requested:
            continue
        image_args = ['RGBA', (w, h)]
        if background != 'transparent':
            image_args.append(background)
        result = Image.new(*image_args)
        final_draw = ImageDraw.Draw(result)
        final_draw.text((-ax0+padding, -ay0+padding), text, font=font, fill=foreground)
        filename = f'{foreground[0]}o{background[0]}.png'
        if name is not None:
            filename = f'{name}-{filename}'
        result.save(filename, 'PNG')

