#!/usr/bin/env python2
# coding: utf8

import sys
import textwrap
import collections
from optparse import OptionParser

Symbols = collections.namedtuple('Symbols',
                                 'corner straight range joint')
_PRESETS = {
    'ASCII':   Symbols(u'\\- ', u'|', u'\\_/', u'_',),
    'UNICODE': Symbols(u'└ ', u'│', u'└─┘', u'┬'),
    'ROUNDED': Symbols(u'╰ ', u'│', u'╰─╯', u'┬'),
    'DOUBLE':  Symbols(u'╚ ', u'║', u'╚═╝', u'╦'),
    'BOLD':    Symbols(u'┗ ', u'┃', u'┗━┛', u'┳'),
}

class Explainer(object):
    def __init__(self):
        """Set default options."""

        self.line_len = 72
        self.symbols = _PRESETS['ASCII']

    def explain(self, text):
        """Parse and annotate the given text.

        This is meant to be the method that's used by you.

        Returns a list of annotated commands.
        """

        explained = []
        indexed = self.parse_plaintext_explanation(text)
        for (cmd, indexed_comments) in indexed:
            explained += [self.annotate_indexed_comments(cmd,
                indexed_comments)]
        return explained

    def parse_plaintext_explanation(self, content):
        """Find out which ranges the comments apply to.

        Returns a list of tuples.  Each tuple contains one command and
        the list of associated comments (including the range for each
        comment).
        """

        # Split and filter lines.  The last empty line ensures that the
        # end of the last comment will be detected.
        lines = content.split('\n')
        lines = [i for i in lines if len(i) == 0 or i[0] != ';']
        lines += ['']

        all_explanations = []
        while len(lines) > 0:
            # The command itself is in the very first line.
            cmd = lines.pop(0)
            if cmd == '':
                continue

            # Read the markers and store their ranges.
            markers = lines.pop(0) + ' '
            indexes = []
            start = -1
            for i in range(len(markers)):
                c = markers[i]
                if c == '-' and start == -1:
                    start = i
                elif c == ' ' and start != -1:
                    indexes += [(start, i - start)]
                    start = -1
                elif c == '+' and start != -1:
                    indexes += [(start, i - start + 1)]
                    start = -1
                elif c == '!':
                    if start != -1:
                        indexes += [(start, i - start)]
                    indexes += [(i, 1)]
                    start = -1

            # Extract comments.
            comments = []
            one_comment = []
            at = 0
            while len(lines) > 0 and at < len(indexes):
                line = lines.pop(0).strip()
                if line == '' and len(one_comment) > 0:
                    one_comment = ' '.join(one_comment)
                    comments += [one_comment]
                    one_comment = []
                    at += 1

                elif line != '':
                    # Replace a trailing '\\' with an artifical newline.
                    if line.endswith(r'\\'):
                        line = line[:-2] + '\n'
                    one_comment += [line]

            # No comments or no indices were found.
            if len(comments) == 0:
                all_explanations += [(cmd, None)]
                continue

            # Associate comments with their ranges.
            indexed_comments = zip(indexes, comments)
            indexed_comments = map(lambda ((start, length), comment):
                    (start, length, comment), indexed_comments)

            all_explanations += [(cmd, indexed_comments)]

        return all_explanations

    def annotate_indexed_comments(self, cmd, indexed_comments):
        """Explain one single command.

        Given a command and a list of indexed comments, explain the
        command by drawing lines from the comments to the associated
        parts of the command.

        Returns the annotated command as a string.
        """

        if indexed_comments is None:
            return cmd + '\n'

        indexed_comments.reverse()

        # We *need* the lines to be at least as long as the command.
        # Additionally, add some space to the right which is needed for
        # the comments.
        line_len = max(self.line_len, len(cmd) + 10)

        # Our "drawing" will start with an initial empty line.
        empty_line = ' ' * line_len
        drawing = [list(empty_line)]
        y = 1

        # If the comment on the very right is associated with a range
        # greater than 2, then add an additional empty line.  This is
        # done because we want to show a "|" over each corner.  If we
        # didn't add the extra line, the "|" would be missing.
        if indexed_comments[0][1] > 2:
            drawing += [list(empty_line)]
            y += 1

        # Add the corner symbol and the wrapped comment.  Keep track of
        # where we placed the corners.  Every line will be at least
        # "line_len" characters long.  This allows us to draw arrows and
        # stuff later on.
        corners = []
        for i in range(len(indexed_comments)):
            (start, length, comment) = indexed_comments[i]

            # Don't move the graph to the right if length is too short.
            skip = 0
            if length >= 3:
                skip = length / 2

            # The indented corner.
            line_to_add = ' ' * start
            line_to_add += ' ' * skip
            line_to_add += self.symbols.corner
            y += 1

            # Remember this corner.
            corners += [(start + skip, y)]

            # Remaining width for this comment.
            comment_width = line_len - start - skip - len(self.symbols.corner)

            # Wrapping: Honor manual newlines first.
            pre_wrapped = comment.split('\n')
            pre_wrapped = [line.strip() for line in pre_wrapped if line != '']

            # Now wrap each line individually.
            wrapped = []
            for line in pre_wrapped:
                wrapped += textwrap.wrap(line, comment_width)

            # Add the comment's first line after the corner and insert
            # it into the drawing.
            line_to_add += wrapped.pop(0)
            drawing += [list(line_to_add)]

            # Add remaining lines.  All of them have to be properly
            # indented.
            for line in wrapped:
                line_to_add = ' ' * (start + skip + len(self.symbols.corner))
                line_to_add += line
                drawing += [list(line_to_add)]
                y += 1

            # If this is not the very last comment, then add an extra
            # line.
            if i < len(indexed_comments) - 1:
                drawing += [list(empty_line)]
                y += 1

        # Draw the lines from the corners up to the command.
        for x, y in corners:
            for i in range(y - 1):
                drawing[i][x] = self.symbols.straight

        # Draw ranges if they're greater 2.
        for (start, length, _) in indexed_comments:
            if length < 3:
                continue

            drawing[0][start] = self.symbols.range[0]
            drawing[0][start + length - 1] = self.symbols.range[2]

            for i in range(start + 1, start + length - 1):
                drawing[0][i] = self.symbols.range[1]

            drawing[0][start + length / 2] = self.symbols.joint

        # Convert it to a string and remove trailing whitespace.
        drawing = [''.join(line).rstrip() for line in drawing]
        drawing = '\n'.join(drawing)

        # Prepend the command and return the result.
        return cmd + '\n' + drawing + '\n'

if __name__ == '__main__':
    # Create a new Explainer object.  Read its default settings and use
    # them as the default command line options.
    explainer = Explainer()

    parser = OptionParser(usage='usage: %prog [options] [file]...')
    parser.add_option('-w', '--width', dest='line_len',
                      help='Maximum width of output. Defaults to ' +
                      '%default.',
                      default=explainer.line_len, type='int')
    parser.add_option('-c', '--corner', dest='corner',
                      help='Characters to use as corners (overrides ' +
                      'the preset).', default=None)
    parser.add_option('-s', '--straight', dest='straight',
                      help='Character to use as straight lines ' +
                      '(overrides the preset).', default=None)
    parser.add_option('-r', '--range', dest='range',
                      help='Characters to use for ranges (overrides ' +
                      'the preset).', default=None)
    parser.add_option('-j', '--joint', dest='joint',
                      help='Character to use for joints between ' +
                      'lines and ranges (overrides the preset).',
                      default=None)
    parser.add_option('-P', '--preset', dest='preset',
                      help='Use the specified preset list of ' +
                      'box-drawing chars. May be one of %s ' %
                      ', '.join(_PRESETS.keys()) + '(case ' +
                      'insensitive). Defaults to "%default".',
                      default='ASCII')
    parser.add_option('-S', '--show-characters', dest='show_chars',
                      help='Only dump the symbol set and exit. Does ' +
                      'not process any input.',
                      default=False, action='store_true')
    parser.add_option('-u', '--unicode', dest='preset',
                      help='Use a preset of unicode glyphs for the '
                      + 'graph. This is equivalent to \'-P unicode\'.',
                      action='store_const', const='UNICODE')
    parser.add_option('-8', '--dont-force-utf-8', dest='force_utf8',
                      help='Do not enforce UTF-8 as output encoding.',
                      default=True, action='store_false')

    (options, args) = parser.parse_args()

    # Apply symbol preset if available.
    try:
        explainer.symbols = _PRESETS[options.preset.upper()]
    except KeyError:
        print >> sys.stderr, 'Symbol preset %r unsupported.' % \
                             options.preset.upper()
        sys.exit(1)

    # Single symbols override those of the preset.
    if not options.corner is None:
        explainer.symbols = explainer.symbols._replace(
                            corner=options.corner.decode('UTF-8'))
    if not options.straight is None:
        explainer.symbols = explainer.symbols._replace(
                            straight=options.straight.decode('UTF-8'))
    if not options.range is None:
        explainer.symbols = explainer.symbols._replace(
                            range=options.range.decode('UTF-8'))
    if not options.joint is None:
        explainer.symbols = explainer.symbols._replace(
                            joint=options.joint.decode('UTF-8'))

    # Simply dump the set of symbols?
    if options.show_chars:
        for t in explainer.symbols._asdict().items():
            print '%s = \'%s\'' % t
        sys.exit(0)

    # Copy desired line length.
    explainer.line_len = options.line_len

    # Read all files or stdin and annotate the commands.
    if len(args) > 0:
        explained = []
        for i in args:
            try:
                with open(i, 'r') as fp:
                    content = fp.read().decode('UTF-8')
                    explained += explainer.explain(content)
            except IOError as (errno, errstr):
                print >> sys.stderr, 'Can\'t read %s: %s' % (i, errstr)
                sys.exit(1)
    else:
        try:
            content = sys.stdin.read().decode('UTF-8')
            explained = explainer.explain(content)
        except KeyboardInterrupt:
            sys.exit(1)

    explained = '\n'.join(explained)

    # Enforce UTF-8?  This is needed when piping the output to another
    # program.  Can be turned off, though.
    if options.force_utf8:
        print explained.encode('UTF-8'),
    else:
        print explained,

# vim: set ts=4 sw=4 et :
