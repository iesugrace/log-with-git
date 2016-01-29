import os, sys
import applib
import interact

class Git:
    """ Git related operations
    """
    SUCCESS  = 0
    TOFETCH  = 1
    CONFLICT = 2
    NOREMOTE = 3
    UNKNOWN  = 4

    def __init__(self, gitWorkTree, gitDir=None):
        if gitDir is None:
            gitDir = os.path.join(gitWorkTree, '.git')
        self.gitWorkTree = gitWorkTree
        self.gitDir      = gitDir
        if not os.path.exists(gitDir):
            self.init()

    def commit(self, paths, message):
        """ Add the files of paths and create a commit

        'paths' is a list of file paths, '-A' option
        makes git to add the deleted files.
        """
        cmd = ['git', 'add', '-A'] + paths
        res = self.runCmd(cmd)
        if not res[0]:
            return False
        cmd = ['git', 'commit', '-m', message]
        self.runCmd(cmd)

    def init(self):
        """ Initialize a git repository
        """
        cmd = ['git', 'init']
        self.runCmd(cmd)

    def runCmd(self, cmd, quiet=False):
        """ Switch the working directory to the
        GIT_DIR, then run git command there,
        and then switch back.
        """
        owd = os.getcwd()
        os.chdir(self.gitWorkTree)
        res = applib.get_status_byte_output(cmd)
        if not res[0] and not quiet:
            print('git command failed:', file=sys.stderr)
            print(res[2].decode(), file=sys.stderr, end='')
        os.chdir(owd)
        return res

    def last(self):
        """ Return the file path of the last commit
        it's a relative path, and one file only.
        """
        path = None
        cmd  = ['git', 'log', '-1', '--pretty=format:', '--name-only']
        stat, stdout, stderr = self.runCmd(cmd, quiet=True)
        if stat:
            path = stdout.decode().strip().split('\n')[0]
        path = path if path else None
        return path

    def shadowInit(self):
        """ Initialize the shadow git
        """
        cmd = ['git', 'shadow-init', '-s']
        stat, *junk = self.runCmd(cmd, quiet=True)
        if stat:
            return True
        print('shadow git not initialized, initializing...')
        owd = os.getcwd()
        os.chdir(self.gitWorkTree)
        stat = os.system('git shadow-init')
        os.chdir(owd)
        return stat == 0

    def setRemote(self, remote):
        """ Add the remote to git if it does not yet exist
        """
        cmd = ['git', 'remote']
        stat, stdout, stderr = self.runCmd(cmd, quiet=True)
        lines = stdout.split(b'\n')
        if remote.encode() in lines:
            return True
        print('remote "%s" not exists, adding...' % remote)
        addr = interact.readstr('address: ')
        cmd = ['git', 'remote', 'add', remote, addr]
        stat, stdout, stderr = self.runCmd(cmd, quiet=True)
        return stat

    def shadowPush(self, remote, branch='master'):
        """ Do a shadow-push
        """
        cmd = ['git', 'shadow-push', remote, branch]
        stat, stdout, stderr = self.runCmd(cmd, quiet=True)
        if not stat:
            if (b'[rejected]' in stderr and
                (b'the remote contains work' in stderr or
                 b'non-fast-forward' in stderr)):
                code = Git.TOFETCH
            else:
                code = Git.UNKNOWN
        else:
            code = Git.SUCCESS
        return (code, stderr)

    def shadowFetch(self, remote, branch='master'):
        """ Do a shadow-fetch
        """
        cmd = ['git', 'shadow-fetch', remote, branch]
        stat, stdout, stderr = self.runCmd(cmd, quiet=True)
        return (stat, stderr)

    def shadowMerge(self, remote, branch='master'):
        """ Do a shadow-merge
        """
        code = Git.UNKNOWN
        cmd  = ['git', 'checkout', branch]
        stat, stdout, stderr = self.runCmd(cmd, quiet=True)
        if stat:
            plainBranch = 'plain-%s-%s' % (remote, branch)
            cmd = ['git', 'shadow-merge', plainBranch]
            stat, stdout, stderr = self.runCmd(cmd, quiet=True)
            if not stat:
                if b'CONFLICT' in stderr:
                    code = Git.CONFLICT
            else:
                code = Git.SUCCESS
        return (code, stderr)

    def allRemotes(self):
        """ Return a list of all remotes
        """
        cmd  = ['git', 'remote']
        stat, stdout, stderr = self.runCmd(cmd, quiet=True)
        res = stdout.decode().split('\n')
        res = [x for x in res if x]
        return res
