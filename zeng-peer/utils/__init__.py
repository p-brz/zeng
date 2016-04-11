from defs import DEBUG


def log_debug(*message):
    if DEBUG:
        print(*message)
