#!/usr/bin/env python

import argparse
import os
import sys
from argparse import RawDescriptionHelpFormatter
from os import path


class Cli(object):
    class Arguments(object):
        def __init__(self):
            self.alias = None
            self.host = None
            self.dir = os.getcwd()

    class Parser(object):
        def __init__(self):
            description = ("Shares a directory with a remote peer "
                           "or connect with a remote shared folder."
                           "\n\nEx: "
                           "\nsteve@hostA {0} . {1}"
                           "\n\tstart sharing the current dir "
                           "with the name '{1}'\n"
                           "\njohn@hostB {0} {1}@{2}"
                           "\n\tconnect with the remote "
                           "directory at ip '{2}'").format(sys.argv[0],
                                                           'shareddir',
                                                           '10.0.0.10')

            self.parser = argparse.ArgumentParser(
                formatter_class=RawDescriptionHelpFormatter,
                description=description
                )

            self.parser.add_argument(
                "dir", nargs='?', default=os.getcwd(),
                help="the shared directory used by zeng."
                "Defaults to the current dir.")

            self.parser.add_argument(
                "alias", nargs='?', default=None,
                help="The name used by peers to connect with the shared dir."
                "Defaults to the directory name")

        def parse(self):
            args = self.parser.parse_args()

            parts = args.dir.split("@")

            cliArgs = Cli.Arguments()

            if len(parts) >= 2:
                cliArgs.alias = parts[0]
                cliArgs.host = parts[1]
                cliArgs.dir = os.getcwd()
            else:
                cliArgs.dir = path.realpath(args.dir)
                cliArgs.alias = self._getarg(
                    args, 'alias', path.basename(cliArgs.dir)
                    )
                cliArgs.host = None

            return cliArgs

        def _getarg(self, args, argname, default=None):
            value = getattr(args, argname, default)
            return value if value is not None else default
