==============================================================================
 flymake-python: highlight Python syntax, style and unit test errors in Emacs
==============================================================================

This project includes tools for enabling Emacs to run external Python
lint and unit testing tools in the background while editing and
highlighting the results in the source code.


Features
========

The following external tools are supported:

* pep8.py
* PyChecker
* PyLint
* PyFlakes
* nose

Python virtual environments are supported, but this is largely
untested.


Components
==========

``pyflymake.py``:
    a script which runs external tools according to user's
    configuration and parses the output for ``flymake.el``.  The
    script is based on code copied from the Emacs Wiki on 2010-02-25.
    The original author is unknown.

``flymake.el``:
    a modified version of Pavel Kabyakov's ``flymake.el`` 0.3 which
    adds support for

    * the 'info' message type in addition to 'error' and 'warning'
    * passing the reason for running to external tools

``.emacs`` customization:
    in addition, a snippet of Emacs Lisp is needed in your ``~/.emacs``
    file


Installation
============

Prerequisites
-------------

Install or make sure you have installed:

* Emacs (tested on 23.1.50.1)
* Python (tested on 2.6.4)
* the following Python packages:

  * pep8
  * pychecker
  * pylint
  * nose
  * nose_machineout (from http://bitbucket.org/akaihola/nose_machineout/)

Files to install
----------------

Make sure that ``pep8``, ``pylint`` and ``pychecker`` are in your
$PATH.

Choose a directory for ``pyflymake.py`` (e.g. ``~/.emacs.d/``) and
copy it there.  Make sure the script is set as executable.

Copy the provided version of ``flymake.el`` in a directory which is in the Emacs ``load-path``.  If another version of flymake is installed, make sure this directory precedes it.  Example: copy to ``~/.emacs.d/flymake.el`` and add this to your ``~/.emacs`` file::

    (add-to-list 'load-path "~/.emacs.d")

Emacs configuration
-------------------

Add to your ``~/.emacs`` file (customize paths if necessary)::

    (add-to-list 'load-path "~/.emacs.d") ;; check path

    (when (load "flymake" t)
      (defun flymake-pylint-init ()
        (let* ((temp-file (flymake-init-create-temp-buffer-copy
                           'flymake-create-temp-inplace))
               (local-file (file-relative-name
                            temp-file
                            (file-name-directory buffer-file-name))))
          (list "~/.emacs.d/pyflymake.py" (list local-file))))
	  ;;     check path

      (add-to-list 'flymake-allowed-file-name-masks
		   '("\\.py\\'" flymake-pylint-init)))

If you'd like flymake to be activated automatically, add the following to
``~/.emacs`` as well::

    (add-hook 'find-file-hook 'flymake-find-file-hook)

See the ``flymake-customizations.el`` file for a more advanced set of
customizations and keybindings.

Configuration
=============

By default, ``pyflymake.py`` only runs PyLint, Pep8 and PyFlakes.
PyChecker and unit test runners can be enabled in the configuration.

To find the configuration, ``pyflymake.py`` looks for ``.pyflymakerc``
in the same directory as the file being checked.  If it isn't found,
parent directories are checked up until the root directory.  If no
configuration file is found, the default configuration is used.

The ``.pyflymakerc`` configuration file is imported by
``pyflymake.py`` as a Python module.  The ``TRIGGER_TYPE`` global
variable is set and contains a string indicating the reason why
flymake is running the checks.

List of configuration options
-----------------------------

``VIRTUALENV`` (default: ``None``)
    the Python virtual environment to use when running check tools

``TEST_RUNNER_COMMAND`` (default: ``None``)
    the unit test runner command or ``None`` if no unit tests should
    be run

``TEST_RUNNER_FLAGS`` (default: ``[]``)
    the list of command line arguments for the unit test runner

``TEST_RUNNER_OUTPUT`` (default: ``'stderr'``)
    the device on which messages are output by the test runner

``ENV`` (default: ``{}``)
    additional environment variables when running check tools

``PYLINT`` (default: ``True``)
    enable PyLint

``PYCHECKER`` (default: ``False``)
    enable PyChecker

``PEP8`` (default: ``True``)
    enable Pep8

``PYFLAKES`` (default: ``True``)
    enable PyFlakes

``IGNORE_CODES`` (default: ``(``))
    error codes to ignore (in addition to sane defaults)

``IGNORE_CODES_PYLINT`` (default: ``(``))
    error codes to ignore in PyLint

``IGNORE_CODES_PYCHECKER`` (default: ``(``))
    error codes to ignore in PyChecker

``IGNORE_CODES_PEP8`` (default: ``(``))
    error codes to ignore in Pep8

``IGNORE_CODES_PYFLAKES`` (default: ``(``))
    error codes to ignore in PyFlakes

``USE_SANE_DEFAULTS`` (default: ``True``)
    ignore the following error codes in PyLint:

    * ``C0103`` Naming convention
    * ``C0111`` Missing Docstring
    * ``E1002`` Use super on old-style class
    * ``W0232`` No ``__init__``
    * ``R0904`` Too many public methods
    * ``R0903`` Too few public methods
    * ``R0201`` Method could be a function

Enabling a unit test runner
---------------------------

In the root of a source tree in which you want pyflymake to run tests,
create the file ``.pyflymakerc`` with the following content::

    # to run external tools in a virtualenv:
    VIRTUALENV = '/home/me/.virtualenvs/thevirtualenv'

    # to run unit tests with nose:
    TEST_RUNNER_COMMAND = 'nosetests'
    TEST_RUNNER_FLAGS = [
        '--verbosity=0',
        '--with-machineout',
        '--machine-output']

    # to enable additional checks:
    PYCHECKER = True

You can use different test runners, too, provided that their output is
similar to nose_machineout's.  For example, Django's test runner could
be used if django-nose is installed::

    TEST_RUNNER_COMMAND = '/home/me/project/manage.py'
    TEST_RUNNER_FLAGS = [
        'test',
        '--settings=test_settings',
        '--failfast',
        '--verbosity=0',
        '--with-machineout',
        '--machine-output']

Trigger type specific configuration
-----------------------------------

You can specify custom configurations depending on why the checks are
being run.  Different triggers for ``flymake.el`` to run the checks
are:

* ``open``: ``flymake.el`` was activated for the buffer
* ``edit``: the buffer was edited more than .5 seconds ago
* ``save``: the buffer was saved
* ``force``: ``M-x flymake-start-syntax-check`` was executed manually

Here's an example configuration::

    # run unit tests only when checks are forced or buffer saved
    if TRIGGER_TYPE in ('save', 'force'):
        TEST_RUNNER_COMMAND = 'nosetests'
        TEST_RUNNER_FLAGS = [
            '--verbosity=0',
            '--with-machineout',
            '--machine-output']

    # run unit tests only up to the first failure when buffer is saved
    if TRIGGER_TYPE == 'save':
        TEST_RUNNER_FLAGS.append('-x')

    # run PyLint on open, save and forced-checks
    PYLINT = TRIGGER_TYPE != 'edit'

    # don't ignore any messages when a check was forced
    if TRIGGER_TYPE == 'force':
        USE_SANE_DEFAULTS = False
        IGNORE_CODES = ()

Donations
---------

If you'd like to support ongoing development of this tool,
feel free to send a Bitcoin tip to
1Pq1Y6AJjhL3rjGYW7CNKX2vhw4yDo3qdV
