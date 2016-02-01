import sys


class Colors(object):
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def progress_bar(title, progress, warning=""):
    bar_length = 50
    status = ""

    if isinstance(progress, int):
        progress = float(progress)

    if progress < 0:
        progress = 0
        status = "Halt...\r\n"

    if progress >= 1:
        progress = 1
        status = "Done...\r\n"

    block = int(round(bar_length * progress))
    text = '\r{0}{1}: {2}[{3}{4}{5}{6}] {7}% {8}{9}'.format(Colors.OKBLUE,
                                                      title[0:20].ljust(20),
                                                      Colors.ENDC,
                                                      Colors.OKGREEN,
                                                      "#" * block,
                                                      "-" * (bar_length - block),
                                                      Colors.ENDC,
                                                      int(round(progress * 100)),
                                                      status,
                                                      Colors.WARNING + warning)
    sys.stdout.write(text)
    sys.stdout.flush()
