#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import imp
import logging

from subprocess import Popen, PIPE

MAX_DESCRIPTION_LENGTH = 60

class LintRunner(object):
    """ Base class provides common functionality to run
          python code checkers. """

    sane_default_ignore_codes = set([])
    command = None
    output_matcher = None

    #flymake: ("\\(.*\\) at \\([^ \n]+\\) line \\([0-9]+\\)[,.\n]" 2 3 nil 1)
    #or in non-retardate: r'(.*) at ([^ \n]) line ([0-9])[,.\n]'
    output_format = ("%(level)s %(tool)s/%(error_type)s%(error_number)s:"
                     "%(description)s at %(filename)s line %(line_number)s.")

    def __init__(self, config):
        self.config = config
        if self.config.VIRTUALENV:
            # This is the least we can get away with (hopefully).
            self.env = {
                'VIRTUAL_ENV': self.config.VIRTUALENV,
                'PATH': self.config.VIRTUALENV + '/bin:' + os.environ['PATH']}
        else:
            self.env = {}

        self.env.update(self.config.ENV)

    @property
    def operative_ignore_codes(self):
        if self.config.USE_SANE_DEFAULTS:
            return self.config.IGNORE_CODES ^ self.sane_default_ignore_codes
        else:
            return self.config.IGNORE_CODES

    @property
    def run_flags(self):
        return ()

    @staticmethod
    def fixup_data(data):
        return data

    @property
    def stream(self):
        return 'stdout'

    @classmethod
    def process_output(cls, line):
        m = cls.output_matcher.match(line)
        if m:
            fixed_data = dict.fromkeys(('level', 'error_type',
                                        'error_number', 'description',
                                        'filename', 'line_number'),
                                       '')
            fixed_data['tool'] = cls.__name__.split('Runner')[0].lower()
            fixed_data.update(cls.fixup_data(m.groupdict()))
            if len(fixed_data['description']) > MAX_DESCRIPTION_LENGTH:
                # truncate long descriptions
                fixed_data['description'] = (
                    '%s...' %
                    fixed_data['description'][:MAX_DESCRIPTION_LENGTH - 3])
            print cls.output_format % fixed_data

    def run(self, filename):
        cmdline = [self.command]
        cmdline.extend(self.run_flags)
        cmdline.append(filename)

        env = dict(os.environ, **self.env)
        logging.debug(' '.join(cmdline))
        process = Popen(cmdline, stdout=PIPE, stderr=PIPE, env=env)

        for line in getattr(process, self.stream):
            self.process_output(line)

        if logging.getLogger().isEnabledFor(logging.DEBUG):
            other_stream = ('stdout', 'stderr')[self.stream == 'stdout']
            for line in getattr(process, other_stream):
                logging.debug('%s %s: %s',
                              self.__class__.__name__, other_stream, line)


class PylintRunner(LintRunner):
    """ Run pylint, producing flymake readable output.

    The raw output looks like:
      render.py:49: [C0301] Line too long (82/80)
      render.py:1: [C0111] Missing docstring
      render.py:3: [E0611] No name 'Response' in module 'werkzeug'
      render.py:32: [C0111, render] Missing docstring """

    output_matcher = re.compile(
        r'(?P<filename>.+):'
        r'(?P<line_number>\d+):'
        r'\s*\[(?P<error_type>[WECR])(?P<error_number>[^,]+),'
        r'\s*(?P<context>[^\]]+)\]'
        r'\s*(?P<description>.*)$')

    command = 'python'

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

    fixup_map = {'E': 'error', 'C': 'info', None: 'warning'}

    @staticmethod
    def fixup_data(data):
        fixup_map = PylintRunner.fixup_map
        data['level'] = fixup_map.get(data['error_type'][0], fixup_map[None])
        return data

    @property
    def run_flags(self):
        return ('-c',
                'import sys,pylint.lint;pylint.lint.Run(sys.argv[1:])',
                '--output-format', 'parseable',
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

    command = 'python'

    output_matcher = re.compile(
        r'(?P<filename>.+):'
        r'(?P<line_number>\d+):'
        r'\s+(?P<description>.*)$')

    @staticmethod
    def fixup_data(data):
        #XXX: doesn't seem to give the level
        data['level'] = 'warning'
        return data

    @property
    def run_flags(self):
        return ('-c',
                ('import sys;'
                 'import pychecker.checker;'
                 'pychecker.checker.main(sys.argv)'),
                '--no-deprecated',
                '-0186',
                '--only',
                '-#0')


class PyflakesRunner(LintRunner):
    command = 'python'

    output_matcher = re.compile(
        r'(?P<filename>.+):'
        r'(?P<line_number>\d+):'
        r'\s+(?P<description>.*)$')

    @staticmethod
    def fixup_data(data):
        #XXX: doesn't seem to give the level
        data['error_type'] = 'W'
        data['level'] = 'warning'
        return data

    @property
    def stream(self):
        return 'stdout'

    @property
    def run_flags(self):
        return ('-c',
                ('import sys;'
                 'from pyflakes.scripts import pyflakes;'
                 'pyflakes.main(sys.argv[1:])'))


class Pep8Runner(LintRunner):
    """ Run pep8.py, producing flymake readable output.

    The raw output looks like:
      spiders/structs.py:3:80: E501 line too long (80 characters)
      spiders/structs.py:7:1: W291 trailing whitespace
      spiders/structs.py:25:33: W602 deprecated form of raising exception
      spiders/structs.py:51:9: E301 expected 1 blank line, found 0 """

    command = 'pep8'
    # sane_default_ignore_codes = set([
    #     'RW29', 'W391',
    #     'W291', 'WO232'])

    output_matcher = re.compile(
        r'(?P<filename>.+):'
        r'(?P<line_number>[^:]+):'
        r'[^:]+:'
        r' (?P<error_number>\w+) '
        r'(?P<description>.+)$')

    @staticmethod
    def fixup_data(data):
        if 'W' in data['error_number']:
            data['level'] = 'info'
        else:
            data['level'] = 'info'

        return data

    @property
    def run_flags(self):
        return '--repeat', '--ignore=' + ','.join(self.config.IGNORE_CODES)


class TestRunner(LintRunner):
    """ Run unit tests, producing flymake readable output."""

    @property
    def command(self):
        return self.config.TEST_RUNNER_COMMAND

    output_matcher = re.compile(
        r'(?P<filename>.+):'
        r'(?P<line_number>[^:]+): '
        r'In (?P<function>[^:]+): '
        r'(?P<error_number>[^:]+): '
        r'(?P<description>.+)$')

    LEVELS = {'fail': 'error'}

    @staticmethod
    def fixup_data(data):
        data['level'] = TestRunner.LEVELS.get(data['error_number'], 'warning')

        return data

    @property
    def stream(self):
        return self.config.TEST_RUNNER_OUTPUT

    @property
    def run_flags(self):
        return self.config.TEST_RUNNER_FLAGS


def find_config(path, trigger_type):
    if path in ('', '/'):
        module = DefaultConfig()
    else:
        try:
            parent_dir = os.path.join(path, '.pyflymakerc')
            # dirtiest trick ever:
            __builtins__.TRIGGER_TYPE = trigger_type
            module = imp.load_source('config', parent_dir)
            del __builtins__.TRIGGER_TYPE
        except IOError:
            module = find_config(os.path.split(path)[0], trigger_type)
    return module


class DefaultConfig(object):
    def __init__(self):
        self.VIRTUALENV = None
        self.TEST_RUNNER_COMMAND = None
        self.TEST_RUNNER_FLAGS = []
        self.TEST_RUNNER_OUTPUT = 'stderr'
        self.ENV = {}
        self.PYLINT = True
        self.PYCHECKER = False
        self.PEP8 = True
        self.PYFLAKES = True
        self.IGNORE_CODES = ()
        self.USE_SANE_DEFAULTS = True

DEFAULT_CONFIG = dict(
    VIRTUALENV=None,
    TEST_RUNNER_COMMAND=None,
    TEST_RUNNER_FLAGS=[],
    TEST_RUNNER_OUTPUT='stderr',
    ENV={},
    PYLINT=True,
    PYCHECKER=False,
    PEP8=True,
    PYFLAKES=True,
    IGNORE_CODES=(),
    USE_SANE_DEFAULTS=True)


def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-e", "--virtualenv",
                      dest="virtualenv",
                      default=None,
                      help="virtualenv directory")
    parser.add_option("-t", "--trigger-type",
                      dest="trigger_type",
                      default=None,
                      choices=('open', 'edit', 'save', 'force'),
                      help="flymake trigger type")
    parser.add_option("-i", "--ignore_codes",
                      dest="ignore_codes",
                      default=None,
                      help="error codes to ignore")
    parser.add_option("-d", "--debug",
                      action='store_true',
                      dest="debug",
                      help="print debugging on stderr")
    options, args = parser.parse_args()

    logging.basicConfig(
        level=options.debug and logging.DEBUG or logging.WARNING,
        format='%(levelname)-8s %(message)s')

    config = find_config(os.path.realpath(args[0]), options.trigger_type)
    for key, value in DEFAULT_CONFIG.items():
        if not hasattr(config, key):
            setattr(config, key, value)

    for option in 'virtualenv', 'ignore_codes':
        value = getattr(options, option)
        if value is not None:
            setattr(config, option.upper(), value)
    config.IGNORE_CODES = set(config.IGNORE_CODES)

    if config.TEST_RUNNER_COMMAND:
        tests = TestRunner(config)
        tests.run(args[0])

    def run(runner_class):
        runner = runner_class(config)
        runner.run(args[0])

    if config.PYLINT:
        run(PylintRunner)
    if config.PYCHECKER:
        run(PycheckerRunner)
    if config.PEP8:
        run(Pep8Runner)
    if config.PYFLAKES:
        run(PyflakesRunner)

    sys.exit()

if __name__ == '__main__':
    main()
