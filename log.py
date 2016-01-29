import os, sys
from git import Git
from record import Record
from xmlstorage  import XmlStorage
import applib
import timeutils
from common import editContent
import interact

class Log:
    """ Log management class
    """

    def __init__(self, config):
        self.config = config
        dataDir = config['dataDir']
        os.makedirs(dataDir, exist_ok=True)
        self.git = Git(dataDir)

        # Setup and register storage engine
        XmlStorage.dataDir = dataDir
        XmlStorage.git     = self.git
        Record.engine      = XmlStorage

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
            record = Record.load(path)
        return record

    def add(self, interactive=False, **fields):
        """ Add a log record to the system
        When interactive is True, ask data for subject, time, scene,
        people, tag, and log data from the use interactively, the
        provided arguments are used as the default value for user's
        choice.
        """

        if interactive:
            fields = self.collectLogInfo(**fields)
        author = '%s <%s>' % (self.config['authorName'],
                              self.config['authorEmail'])
        fields['author'] = author
        assert self.checkRequirement(**fields), "field data not sufficient"
        fields = Record.engine.convertFields(fields.items())
        record = Record(**fields)
        record.save()

    def checkRequirement(self, **args):
        """ Check if all required fields are provided
        """
        desc = Record.fields.items()
        keys = [k for k, v in desc if v.get('required') == True]
        for key in keys:
            if not args.get(key):
                print('%s is required' % key, file=sys.stderr)
                return False
        return True

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
                    scene=None, people=None, tag=None, **junk):
        """ Create the necessary requests data for collecting
        information for a Record from the user interactively.
        """
        if record:      # a Record instance provided
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
                lastLog = self.lastLog()
                scene   = self.lastScene(lastLog)
            if not tag:
                if not lastLog:
                    lastLog = self.lastLog()
                tag = self.lastTag(lastLog)

        requests = []
        # arguments: name, default, datatype, reader, desc
        requests.append(self.makeOneRequest('time',    time,    str, None, 'time'))
        requests.append(self.makeOneRequest('scene',   scene,   str, None, 'scene'))
        requests.append(self.makeOneRequest('people',  people,  str, None, 'people'))
        requests.append(self.makeOneRequest('tag',     tag,     str, None, 'tag'))
        return requests

    def makeLogEntry(self, *junk, **args):
        id     = args.pop('id')
        author = args.pop('author')
        fields = self.collectLogInfo(**args)
        fields['id']     = id
        fields['author'] = author
        assert self.checkRequirement(**fields), "field data not sufficient"
        fields = Record.engine.convertFields(fields.items())
        return Record(**fields)

    def collectLogInfo(self, *junk, **args):
        """ Collect Record fields' info interactively
        'data' in the args must be a bytes which can
        be decoded using utf8, binary data that is
        not utf8 encoded, is not applicable.
        """
        data     = args.pop('data')
        subject  = args.pop('subject')
        binary   = args.pop('binary')

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

        return dict(subject=subject, time=time, scene=scene,
                      people=people, tag=tag, data=data, binary=binary)

    def collectLogs(self, filter=None):
        """ Walk through all log records, collect those
        that passed the filter function matching. Return
        a generator which yields Record instances.
        """
        if not filter:
            filter = lambda record: True
        ids = Record.allIds()
        for id in ids:
            record = Record.load(id)
            if filter(record):
                yield record

    def delete(self, ids, force=False):
        """ Delete the logs whose id is in 'ids', confirm
        before deleting if force is False, partial ID is
        acceptable, so that 297aacc is equivalent of
        297aacc3863171ed86ba89a2ea0e88f9c4d99d48.
        """
        allIds = Record.allIds()
        ids = [storedId for storedId in allIds for id in ids
                    if id and storedId.startswith(id)]
        if force:
            preAction = lambda x: True
        else:
            def preAction(record):
                msg = 'delete %s: %s? ' % (record.id, record.subject)
                ans = interact.readstr(msg, default='N')
                return ans == 'y'
        def postAction(record):
            print('deleted %s' % record.id)

        Record.engine.delete(ids, preAction)

    def edit(self, id):
        """ Edit the log of the given id
        The edited log may be saved to a new directory
        if its timestamp changed, in such case the old
        log will be deleted.
        """
        ids = Record.matchId(id)
        if not ids:
            print('%s not found' % id, file=sys.stderr)
            return
        elif len(ids) > 1:
            id = interact.readstr('multiple match, which one? ')
            assert id, 'invalid id: "%s"' % id

        oldRecord = Record.load(ids[0])
        items = oldRecord.elements().items()
        elements  = dict(oldRecord.elements())
        conv = Record.getConv('time', toRecord=False)
        elements['time'] = conv(elements['time'])
        elements['data'] = elements['data'].encode()
        newRecord = self.makeLogEntry(**elements)
        newRecord.save(oldRecord=oldRecord)

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
