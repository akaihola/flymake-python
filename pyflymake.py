#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys

from subprocess import Popen, PIPE

class LintRunner(object):
    """ Base class provides common functionality to run
          python code checkers. """

    sane_default_ignore_codes = set([])
    command = None
    output_matcher = None

    #flymake: ("\\(.*\\) at \\([^ \n]+\\) line \\([0-9]+\\)[,.\n]" 2 3 nil 1)
    #or in non-retardate: r'(.*) at ([^ \n]) line ([0-9])[,.\n]'
    output_format = "%(level)s %(tool)s/%(error_type)s%(error_number)s:" \
                    "%(description)s at %(filename)s line %(line_number)s."

    def __init__(self, virtualenv=None, ignore_codes=(),
                 use_sane_defaults=True):
        if virtualenv:
            # This is the least we can get away with (hopefully).
            self.env = {'VIRTUAL_ENV': virtualenv,
                        'PATH': virtualenv + '/bin:' + os.environ['PATH']}
        else:
            self.env = None

        self.virtualenv = virtualenv
        self.ignore_codes = set(ignore_codes)
        self.use_sane_defaults = use_sane_defaults

    @property
    def operative_ignore_codes(self):
        if self.use_sane_defaults:
            return self.ignore_codes ^ self.sane_default_ignore_codes
        else:
            return self.ignore_codes

    @property
    def run_flags(self):
        return ()

    @classmethod
    def fixup_data(cls, line, data):
        return data

    @classmethod
    def process_output(cls, line):
        m = cls.output_matcher.match(line)
        if m:
            fixed_data = dict.fromkeys(('level', 'error_type',
                                        'error_number', 'description',
                                        'filename', 'line_number'),
                                       '')
            fixed_data['tool'] = cls.__name__.split('Runner')[0].lower()
            fixed_data.update(cls.fixup_data(line, m.groupdict()))
            print cls.output_format % fixed_data

    def run(self, filename):
        args = [self.command]
        args.extend(self.run_flags)
        args.append(filename)

        process = Popen(args, stdout=PIPE, stderr=PIPE, env=self.env)

        for line in process.stdout:
            self.process_output(line)

class PylintRunner(LintRunner):
    """ Run pylint, producing flymake readable output.

    The raw output looks like:
      render.py:49: [C0301] Line too long (82/80)
      render.py:1: [C0111] Missing docstring
      render.py:3: [E0611] No name 'Response' in module 'werkzeug'
      render.py:32: [C0111, render] Missing docstring """

    output_matcher = re.compile(
        r'(?P<filename>[^:]+):'
        r'(?P<line_number>\d+):'
        r'\s*\[(?P<error_type>[WECR])(?P<error_number>[^,]+),'
        r'\s*(?P<context>[^\]]+)\]'
        r'\s*(?P<description>.*)$')

    command = 'pylint'
    sane_default_ignore_codes = set([
        "C0103",  # Naming convention
        "C0111",  # Missing Docstring
        "E1002",  # Use super on old-style class
        "W0232",  # No __init__
        #"I0011",  # Warning locally suppressed using disable-msg
        #"I0012",  # Warning locally suppressed using disable-msg
        #"W0511",  # FIXME/TODO
        #"W0142",  # *args or **kwargs magic.
        "R0904",  # Too many public methods
        "R0903",  # Too few public methods        
        "R0201",  # Method could be a function
        ])

    @classmethod
    def fixup_data(cls, line, data):
        if data['error_type'].startswith('E'):
            data['level'] = 'ERROR'
        else:
            data['level'] = 'WARNING'
        return data

    @property
    def run_flags(self):
        return ('--output-format', 'parseable',
                '--include-ids', 'y',
                '--reports', 'n',
                '--disable-msg=' + ','.join(self.operative_ignore_codes))

class PycheckerRunner(LintRunner):
    """ Run pychecker, producing flymake readable output.

    The raw output looks like:
      render.py:49: Parameter (maptype) not used
      render.py:49: Parameter (markers) not used
      render.py:49: Parameter (size) not used
      render.py:49: Parameter (zoom) not used """

    command = 'pychecker'

    output_matcher = re.compile(
        r'(?P<filename>[^:]+):'
        r'(?P<line_number>\d+):'
        r'\s+(?P<description>.*)$')

    @classmethod
    def fixup_data(cls, line, data):
        #XXX: doesn't seem to give the level
        data['level'] = 'WARNING'
        return data

    @property
    def run_flags(self):
        return '--no-deprecated', '-0186', '--only', '-#0'

class Pep8Runner(LintRunner):
    """ Run pep8.py, producing flymake readable output.

    The raw output looks like:
      spiders/structs.py:3:80: E501 line too long (80 characters)
      spiders/structs.py:7:1: W291 trailing whitespace
      spiders/structs.py:25:33: W602 deprecated form of raising exception
      spiders/structs.py:51:9: E301 expected 1 blank line, found 0 """

    command = 'pep8.py'
    # sane_default_ignore_codes = set([
    #     'RW29', 'W391',
    #     'W291', 'WO232'])

    output_matcher = re.compile(
        r'(?P<filename>[^:]+):'
        r'(?P<line_number>[^:]+):'
        r'[^:]+:'
        r' (?P<error_number>\w+) '
        r'(?P<description>.+)$')

    @classmethod
    def fixup_data(cls, line, data):
        if 'W' in data['error_number']:
            data['level'] = 'WARNING'
        else:
            data['level'] = 'ERROR'

        return data

    @property
    def run_flags(self):
        return '--repeat', '--ignore=' + ','.join(self.ignore_codes)

def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-e", "--virtualenv",
                      dest="virtualenv",
                      default=None,
                      help="virtualenv directory")
    parser.add_option("-i", "--ignore_codes",
                      dest="ignore_codes",
                      default=(),
                      help="error codes to ignore")
    options, args = parser.parse_args()

    pylint = PylintRunner(virtualenv=options.virtualenv,
                          ignore_codes=options.ignore_codes)
    pylint.run(args[0])

    pychecker = PycheckerRunner(virtualenv=options.virtualenv,
                                ignore_codes=options.ignore_codes)
    pychecker.run(args[0])

    pep8 = Pep8Runner(virtualenv=options.virtualenv,
                      ignore_codes=options.ignore_codes)
    pep8.run(args[0])
    sys.exit()

if __name__ == '__main__':
    main()
