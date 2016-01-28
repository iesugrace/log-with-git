import os, sys
from git import Git
from logrecord import LogRecord
from xmlstorage  import XmlStorage
import applib
import timeutils
from common import editContent
import interact

# Register storage engine
LogRecord.engine  = XmlStorage


class Log:
    """ All log operations defined here
    """

    def __init__(self, config):
        self.config = config
        dataDir = config['dataDir']
        os.makedirs(dataDir, exist_ok=True)
        self.git = Git(dataDir)

    def lastScene(self, record=None):
        """ Fetch the recently used scene from the history
        """
        if not record:
            record = self.lastLog()
        if record:
            return record.scene
        else:
            return ''

    def lastTag(self, record=None):
        """ Fetch the recently used tag from the history
        """
        if not record:
            record = self.lastLog()
        if record:
            return record.tag
        else:
            return ''

    def lastLog(self):
        """ Fetch the most recent log record
        """
        path = self.git.last()
        record = None
        if path != None:
            path = os.path.join(self.config['dataDir'], path)
            record = LogRecord.engine.load(path)
        return record

    def add(self, subject='', time=None, scene='', people='',
            tag='', data=b'', binary=False, interactive=False):
        """ Add a log record to the system
        When interactive is True, ask data for subject, time, scene,
        people, tag, and log data from the use interactively, the
        provided arguments are used as the default value for user's
        choice.
        """

        author = '%s <%s>' % (self.config['authorName'],
                              self.config['authorEmail'])
        if interactive:
            record = self.makeLogEntry(subject=subject, author=author,
                                       time=time, scene=scene, people=people,
                                       tag=tag, data=data, binary=binary)
        else:
            assert (subject != None and subject != ''), "invalid subject"
            if not binary:
                data = data.decode()
            record = LogRecord(subject, author, time, scene,
                               people, tag, data, binary)
        path  = record.save(self.config['dataDir'])
        bname = os.path.basename(path)
        message = 'Add log\n\n%s' % bname
        self.git.commit([path], message)

    def makeOneRequest(self, name, default, datatype, reader, desc):
        """ Create a request entry, used to interactively collect
        information from the user. A request is a dictionary object
        that contains necessary information to interact with the user.
        """
        suffix = (' [%s]: ' % default) if default else ': '
        prompt = desc + suffix
        if reader:
            actual_reader = (lambda prompt, default: reader(prompt, default))
        else:
            actual_reader = reader
        return dict(name=name, prompt=prompt, datatype=datatype,
                    default=default, reader=actual_reader)

    def makeRequests(self, *, record=None, time=None,
                    scene=None, people=None, tag=None):
        """ Create the necessary requests data for collecting
        information for a Record from the user interactively.
        """
        if record:      # a LogRecord instance provided
            time     =  record.time
            scene    =  record.scene
            people   =  record.people
            tag      =  record.tag
        else:
            time      = time if time else timeutils.isodatetime()
            people    = people if people else ''
            recentLog = None
            # take the recently used scene and
            # tag from the most recent log.
            if not scene:
                recentLog = self.lastLog()
                scene     = self.lastScene(recentLog)
            if not tag:
                if not recentLog:
                    recentLog = self.lastLog()
                tag = self.lastTag(recentLog)

        requests = []
        # arguments: name, default, datatype, reader, desc
        requests.append(self.makeOneRequest('time',    time,    str, None, 'time'))
        requests.append(self.makeOneRequest('scene',   scene,   str, None, 'scene'))
        requests.append(self.makeOneRequest('people',  people,  str, None, 'people'))
        requests.append(self.makeOneRequest('tag',     tag,     str, None, 'tag'))
        return requests

    def makeLogEntry(self, *junk, **args):
        """ Make a LogRecord instance interactively
        'data' in the args must be a bytes which can
        be decoded using utf8, binary data that is
        not utf8 encoded, is not applicable.
        """
        data     = args.pop('data')
        binary   = args.pop('binary')
        subject  = args.pop('subject')
        author   = args.pop('author')

        # read subject and data from editor
        if binary:
            iData =  b'\n# Binary data is provided, therefore only the first\n'
            iData += b'# line will be used for subject, empty message aborts.\n'
        elif subject:
            iData = subject.encode()
            if data:
                iData += b'\n\n' + data
        else:
            iData = b''
        oData    = editContent(iData).decode()
        msgLines = oData.split('\n\n')
        subject  = msgLines.pop(0).strip()
        if not binary:  # accept data from editor only for non-binary
            data = '\n\n'.join(msgLines)

        # empty subject, abort
        assert subject != '', "aborting due to empty subject"

        # read other info
        requests = self.makeRequests(**args)
        i        = interact.readMany(requests)
        time     =  i['time']
        scene    =  i['scene']
        people   =  i['people']
        tag      =  i['tag']

        return LogRecord(subject, author, time, scene, people, tag, data, binary)

    def allLogPaths(self):
        """ Return all log records' paths in the file
        system, return a generator.
        """
        dataDir = self.config['dataDir']
        cmd = ['find', dataDir, '-name', '.git', '-prune', '-o', '-type', 'f', '-print0']
        res = applib.get_status_byte_output(cmd)
        if not res[0]:
            print('find command failed:', file=sys.stderr)
            print(res[2].decode(), file=sys.stderr, end='')
            return

        lines = res[1].split(b'\x00')[:-1]   # remove the last empty one
        for path in lines:
            yield path.decode()

    def collectLogs(self, filter=None):
        """ Walk through all log records, collect those
        that passed the filter function matching. Return
        a generator which yields LogRecord instances.
        """
        if not filter:
            filter = lambda record: True
        paths = self.allLogPaths()
        for path in paths:
            record = LogRecord.load(path)
            if filter(record):
                yield record

    def delete(self, ids, force=False):
        """ Delete the logs whose id is in 'ids', confirm
        before deleting if force is False, partial ID is
        acceptable, so that 297aacc is equivalent of
        297aacc3863171ed86ba89a2ea0e88f9c4d99d48.
        """
        paths = self.allLogPaths()
        paths = [path for path in paths for id in ids
                    if id and os.path.basename(path).startswith(id)]
        deletedPaths = []
        for path in paths:
            bname  = os.path.basename(path)
            if not force:
                record = LogRecord.load(path)
                msg = 'delete %s: %s? ' % (bname, record.subject)
                ans = interact.readstr(msg, default='N')
                if ans != 'y':
                    continue
            os.remove(path)
            deletedPaths.append(path)
            print('deleted %s' % bname)
        if deletedPaths:
            bnames = [os.path.basename(x) for x in deletedPaths]
            message = 'Delete log\n\n%s' % '\n'.join(bnames)
            self.git.commit(deletedPaths, message)

    def edit(self, id):
        """ Edit the log of the given id
        The edited log may be saved to a new directory
        if its timestamp changed, in such case the old
        log will be deleted.
        """
        paths        = self.allLogPaths()
        changedFiles = []
        for path in paths:
            if os.path.basename(path).startswith(id):
                oldRecord = LogRecord.load(path)
                elements  = dict(oldRecord.elements())
                oldPath   = elements.pop('path')
                elements['data'] = elements['data'].encode()
                elements['time'] = timeutils.isodatetime(elements['time'])
                newRecord = self.makeLogEntry(**elements)
                if newRecord != oldRecord:
                    if newRecord.time != oldRecord.time:
                        os.remove(oldPath)
                        changedFiles.append(oldPath)
                    fileName = os.path.basename(oldPath)
                    newPath  = newRecord.save(self.config['dataDir'], fileName)
                    changedFiles.append(newPath)
                    message  =  'Change log\n\n%s' % fileName
                    self.git.commit(changedFiles, message)
                break

    def push(self, remote):
        """ Sync with the git server

        Push using shadow-git tools, first shadow-push,
        if rejected because of unfetched update on the
        server side, do a shadow-fetch and shadow-merge,
        then a shadow-push again. In case of conflict
        that can not be automatically resolved, exit,
        after manually solved the conflict, user can
        then try to push again.
        """
        def error(msg):
            print(msg, file=sys.stderr)

        if not self.preAction(remote):
            return False

        for i in range(2):              # try twice at most
            print('pushing...')
            stat, msg = self.git.shadowPush(remote)
            if stat == Git.TOFETCH:
                print('push rejected, need to fetch')
                if self.fetch(remote):
                    continue
            elif stat == Git.UNKNOWN:
                error('unknown error:\n' + msg.decode())
            elif stat == Git.SUCCESS:
                print('push done.')
                return True
            return False


    def preAction(self, remote):
        """ Actions to carry out before push/fetch
        """
        if not self.git.shadowInit():
            return False
        if not self.git.setRemote(remote):
            return False
        return True


    def fetch(self, remote):
        """ Fetch from the git server
        """
        def error(msg):
            print(msg, file=sys.stderr)

        if not self.preAction(remote):
            return False

        print('fetching...')
        stat, msg = self.git.shadowFetch(remote)
        if not stat:
            error('fetch failed:\n' + msg.decode())
        else:
            print('merging...')
            stat, msg = self.git.shadowMerge(remote)
            if stat == Git.SUCCESS:
                print('fetch done.')
                return True
            elif stat == Git.UNKNOWN:
                error('unknown error:\n' + msg.decode())
            elif stat == Git.CONFLICT:
                error('automatic merge failed, fix the conflict, and retry')
        return False
