#!/usr/bin/env python

import argparse
from argparse import RawDescriptionHelpFormatter

import os
from os import path
import sys

class Main(object):
    def __init__(self):
        description = ("Shares a directory with a remote peer or connect with a remote shared folder."
                "\n\nEx: "
                "\nsteve@hostA {0} . {1}"
                "\n\tstart sharing the current dir with the name '{1}'"
                "\n"
                "\njohn@hostB {0} {1}@{2}"
                "\n\tconnect with the remote directory at ip '{2}'").format(sys.argv[0], 'shareddir', '10.0.0.10')

        self.parser = argparse.ArgumentParser(formatter_class=RawDescriptionHelpFormatter
            , description=description)
        self.parser.add_argument("dir", nargs='?', default=os.getcwd()
            , help="the shared directory used by zeng. Defaults to the current dir.")
        self.parser.add_argument("alias", nargs='?', default=None
            , help="the name used by peers to connect with the shared folder. Defaults to the directory name")

    def start(self):
        args = self.parser.parse_args()

        parts = args.dir.split("@")

        if len(parts) >= 2:
            self.alias = parts[0]
            self.host  = parts[1]
            self.dir = None
        else:
            self.dir = path.realpath(args.dir)
            self.alias = self._get_alias_arg(args, self.dir)
            self.host = None

        print("host: ", self.host)
        print("alias: ", self.alias)
        print("dir: ", self.dir)

    def _get_alias_arg(self, args, share_dir):
        if args.alias is not None:
            return args.alias
        else:
            return path.basename(share_dir)

if __name__ == "__main__":
    Main().start()
