from subprocess import Popen, PIPE

class InvalidTimeException(Exception): pass

def get_status_byte_output(cmd):
    """ Run the cmd, return the stdout and stderr as
    bytes objects, as well as the stat of the cmd
    (True or False), cmd is a list.
    """
    p       = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr  = p.communicate()
    stat    = p.wait()
    pStat   = (stat == 0)
    res     = (pStat, stdout, stderr)
    return res


class Pager:
    """ Read data from the stdin, write it
    to the stdout using the LESS program
    """
    prog = 'less'
    def __init__(self, args=[]):
        self.pager = Popen([self.prog] + args, stdin=PIPE)

    def write(self, *chunks, isBytes=True):
        for data in chunks:
            if not isBytes:
                data = data.encode()
            self.pager.stdin.write(data)

    def go(self):
        self.pager.stdin.close()
        self.pager.wait()
