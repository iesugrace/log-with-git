import sys
from git import Git
from record import Record
from xmlstorage  import XmlStorage
from sqlitestorage import SqliteStorage
import applib
from timeutils import isodatetime
from common import editContent
import interact

class Engine:
    """ Management class for engines
    Support to delegate task to multiple engines.
    For better read performance, all read requests
    will be routed to sqlite engine, write requests
    to both. The xml engine serves for assisting
    Git operations.
    """

    engines = {
        'xml':    XmlStorage,
        'sqlite': SqliteStorage,
    }

    def __getattr__(self, name):
        """ All read actions routed to sqlite
        """
        attrList = ['lastLog',
                    'lastLogs',
                    'matchId',
                    'allIds',
                    'load',
                    'searchLogs',
                   ]
        if name in attrList:
            return getattr(self.engines['sqlite'], name)

    def save(self, record, oldRecord=None):
        """ Save record to all engines
        Procedure:
            1. save to sqlite engine, but not commit
            2. save to xml engine (git commit created here)
            3. commit in sqlite if xml engine return success
               or do a roll back
        """
        r = self.engines['sqlite'].save(record, oldRecord, commit=False)
        if r:
            record.id = r.id    # when add, the ID will be new generated.
            r = self.engines['xml'].save(record, oldRecord)
            if r:
                self.engines['sqlite'].commit()
            else:
                print('xml engine failed, roll back sqlite engine actions',
                        file=sys.stderr)
                self.engines['sqlite'].rollback()


    def delete(self, ids, preAction, postAction):
        """ Delete records from all engines
        Procedure:
            1. delete from sqlite engine, but not commit
            2. delete from xml engine (git commit created here)
            3. commit in sqlite if xml engine return success
               or do a roll back
        """
        s = self.engines['sqlite'].delete(ids, preAction, postAction, commit=False)
        if s:
            s = self.engines['xml'].delete(ids) # no need to confirm/inform again
            if s:
                self.engines['sqlite'].commit()
            else:
                print('xml engine failed, roll back sqlite engine actions',
                        file=sys.stderr)
                self.engines['sqlite'].rollback()


class Log:
    """ Log management class
    """

    def __init__(self, config):
        self.config = config
        dataDir     = config['dataDir']

        # Setup and register storage engine
        engine   = Engine()
        eXml     = engine.engines['xml']
        eSqlite  = engine.engines['sqlite']
        self.git = eXml.setup(dataDir)   # Xml storage engine uses git
        eSqlite.setup(dataDir)
        Record.engine = engine

    def lastLog(self):
        """ Fetch the most recent log record
        """
        return Record.engine.lastLog()

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
        fields['mtime']  = isodatetime()    # current time for mtime
        assert self.checkRequirement(**fields), "field data not sufficient"
        fields = Record.convertFields(fields.items())
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

    def makeLogEntry(self, *junk, **args):
        id     = args.pop('id')
        author = args.pop('author')
        fields = self.collectLogInfo(**args)
        fields['id']     = id
        fields['author'] = author
        fields['mtime']  = isodatetime()    # update with current time
        assert self.checkRequirement(**fields), "field data not sufficient"
        fields = Record.convertFields(fields.items())
        return Record(**fields)

    def delete(self, ids, force=False, preAction=None, postAction=None):
        """ Delete the logs whose id is in 'ids', partial
        ID is acceptable, so that 297aacc is the equivalent
        of 297aacc3863171ed86ba89a2ea0e88f9c4d99d48.
        """
        allIds = Record.allIds()
        ids = [storedId for storedId in allIds for id in ids
                    if id and storedId.startswith(id)]
        if force:
            preAction = lambda x: True
        if not preAction:  preAction  = self.preActionOfDelete
        if not postAction: postAction = self.postActionOfDelete
        Record.engine.delete(ids, preAction, postAction)

    def edit(self, id):
        """ Edit the log of the given id
        """
        ids = Record.matchId(id)
        if not ids:
            print('%s not found' % id, file=sys.stderr)
            return
        elif len(ids) > 1:
            prompt   = 'multiple match, which one? '
            junk, id = interact.printAndPick(ids, lineMode=True, prompt=prompt)
            assert id, 'invalid id: "%s"' % id
        else:
            id = ids[0]

        oldRecord = Record.load(id)
        elements  = dict(oldRecord.elements())
        elements  = self.preActionOfEdit(elements)
        newRecord = self.makeLogEntry(**elements)
        newRecord.save(oldRecord=oldRecord)

    def perror(self, msg):
        print(msg, file=sys.stderr)

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
        if not self.preActionOfPushAndFetch(remote):
            return False

        for i in range(2):              # try twice at most
            print('pushing...')
            stat, msg = self.git.shadowPush(remote)
            if stat == Git.TOFETCH:
                print('push rejected, need to fetch')
                if self.fetch(remote):
                    continue
            elif stat == Git.UNKNOWN:
                self.perror('unknown error:\n' + msg.decode())
            elif stat == Git.SUCCESS:
                print('push done.')
                return True
            return False


    def preActionOfPushAndFetch(self, remote):
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
        if not self.preActionOfPushAndFetch(remote):
            return False

        print('fetching...')
        stat, msg = self.git.shadowFetch(remote)
        if not stat:
            self.perror('fetch failed:\n' + msg.decode())
        else:
            print('merging...')
            stat, msg = self.git.shadowMerge(remote)
            if stat == Git.SUCCESS:
                print('fetch done.')
                return True
            elif stat == Git.UNKNOWN:
                self.perror('unknown error:\n' + msg.decode())
            elif stat == Git.CONFLICT:
                self.perror('automatic merge failed, fix the conflict, and retry')
        return False


    """ Methods defined below are Record definition specific,
    subclasses shall redefine/extend these methods according
    to the Record fields definition, or add more others.
    """

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
            time      = time if time else isodatetime()
            people    = people if people else ''
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
        requests.append(applib.makeOneRequest('time',    time,    str, None, 'time'))
        requests.append(applib.makeOneRequest('scene',   scene,   str, None, 'scene'))
        requests.append(applib.makeOneRequest('people',  people,  str, None, 'people'))
        requests.append(applib.makeOneRequest('tag',     tag,     str, None, 'tag'))
        return requests

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

    def preActionOfDelete(self, record):
        """ Confirm before deleting
        """
        msg = 'delete %s: %s? ' % (record.id, record.subject)
        ans = interact.readstr(msg, default='N')
        return ans == 'y'

    def postActionOfDelete(self, record):
        print('deleted %s' % record.id)

    def preActionOfEdit(self, elements):
        """ Convert data before editing
        """
        conv = Record.getConv('time', toRecord=False)
        elements['time'] = conv(elements['time'])
        elements['data'] = elements['data'].encode()
        return elements
