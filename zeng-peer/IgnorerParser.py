import fnmatch


class IgnorerParser(object):

    def __init__(self):
        self.ignore_patterns = []
        self.include_patterns = []

    def start(self, ignore_file):
        with open(ignore_file) as f:
            lines = f.readlines()

            for l in lines:
                l = l.strip()
                if l.startswith("#") or len(l) == 0:
                    continue
                elif l.startswith("!"):
                    self.include_patterns.append(l[1:])
                else:
                    self.ignore_patterns.append(l)

    def ignore(self, filename):
        for inc_patt in self.include_patterns:
            if fnmatch.fnmatch(filename, inc_patt):
                return False

        for ign_patt in self.ignore_patterns:
            if fnmatch.fnmatch(filename, ign_patt):
                return True

        return False
