#!/usr/bin/env python

from cli import Cli
from peer import Peer

class Main(object):
    def start(self):
        args = Cli.Parser().parse()

        print("host: ", args.host)
        print("alias: ", args.alias)
        print("dir: ", args.dir)

        peer = Peer(host=args.host, alias=args.alias, dir=args.dir)

        try:
            peer.start()
        except (KeyboardInterrupt, EOFError):
            peer.stop()
        finally:
            peer.join()

if __name__ == "__main__":
    Main().start()
