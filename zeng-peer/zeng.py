#!/usr/bin/env python

from cli import Cli
from peer import Peer

class Main(object):
    def start(self):
        args = Cli.Parser().parse()

        print("host: ", args.host)
        print("alias: ", args.alias)
        print("dir: ", args.dir)

if __name__ == "__main__":
    Main().start()
