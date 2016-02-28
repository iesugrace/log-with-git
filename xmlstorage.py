import os
from record import Record
from timeutils import isodate
import applib
import re

class XmlStorage:
    """ XML storage engine for the record
    """
    @staticmethod
    def sourceToDom(code):
        """ Parse the raw record data which is XML code,
        return a Xml DOM object.
        """
        from xml.dom.minidom import parseString
        return parseString(code)

    @staticmethod
    def load(id, path=None):
        """ Load the content of the record from disk,
        parse it, and return a record instance.
        """
        if not path:
            path = XmlStorage.idToPath(id)
        try:
            code = open(path).read()
            doc  = XmlStorage.sourceToDom(code)
        except:
            return None

        # collect all fields' data
        fields = {}
        for node in doc.firstChild.childNodes:
            if node.nodeType == node.ELEMENT_NODE:
                name = node.localName
                textNode = node.firstChild
                data = textNode.data if textNode else ''
                fields[name] = data
        fields = XmlStorage.convertFields(fields.items())
        return Record(**fields)

    @staticmethod
    def convertFields(items, toRecord=True):
        """ Convert the data in items to construct a
        record instance if toRecord is True, else
        do a reverse conversion. items is an iterable
        that has key/value items, the key is the name
        of the field, the value is the data to convert.
        Default converter is 'str'.
        """
        res = {}
        idx = 0 if toRecord else 1
        for k, v in items:
            desc = Record.fields.get(k)
            if not desc:    # ignore any fields not defined
                continue
            conv = desc.get('conv', [str, str])[idx]
            res[k] = conv(v)
        return res

    @staticmethod
    def idToPath(id):
        """ Find and return the absolute path of a record
        """
        cmd = 'find %s -name %s' % (XmlStorage.dataDir, id)
        stat, lines = applib.get_status_text_output(cmd)
        if stat and lines:
            return lines[0]
        else:
            return None

    @staticmethod
    def matchId(id):
        """ Return all IDs that starts with 'id'
        """
        cmd = 'find %s -name .git -prune -o -name "%s*" -type f -print'
        cmd = cmd % (XmlStorage.dataDir, id)
        stat, lines = applib.get_status_text_output(cmd)
        ids = list(map(os.path.basename, lines))
        return ids

    @staticmethod
    def createNode(root, nodeName, nodeText):
        """ Add an element node with nodeText to the 'root' element
        """
        from xml.dom.minidom import Element, Text
        ele = Element(nodeName)
        text = Text()
        text.data = nodeText
        ele.appendChild(text)
        root.appendChild(ele)

    @staticmethod
    def recordToSource(record):
        """ Compose Xml source code from a record object
        """
        from xml.dom.minidom import Document, Text
        import re
        doc  = Document()
        root = doc.createElement("log")
        doc.appendChild(root)
        items  = dict(record.elements()).items()
        fields = XmlStorage.convertFields(items, False)

        # sort the fields data according to the definition order
        orders = {k: v['order'] for k, v in Record.fields.items()}
        sortKey = lambda x: orders[x[0]]
        fields = sorted(fields.items(), key=sortKey)

        for name, value in fields:
            XmlStorage.createNode(root, name, value)
        xmlCode = doc.toprettyxml()
        xmlCode = re.sub('\t', ' ' * 4, xmlCode)    # replace tabs with spaces
        return xmlCode

    @staticmethod
    def save(record, oldRecord=None):
        """ Convert the record to Xml code, and Write
        the code to the disk, record id is the basename
        of the record file.

        If the oldRecord is provided, this is to change
        an existing record. When to change an existing
        log, the new log may be saved to a new directory
        if its timestamp been changed, in such case the
        old log will be deleted.
        """
        timestamp  = record.time
        dateEle    = isodate(timestamp).split('-')
        absDirPath = os.path.join(XmlStorage.dataDir, *dateEle)
        paths      = []
        if not oldRecord:   # add new record
            record.id = XmlStorage.genId(timestamp)
            commitMsg = 'Add log\n\n%s' % record.id
        else:
            commitMsg = 'Change log\n\n%s' % record.id
            if record != oldRecord:
                path = XmlStorage.idToPath(oldRecord.id)
                paths.append(path)
                XmlStorage.__delete(None, path=path)
            else:
                return
        os.makedirs(absDirPath, exist_ok=True)
        path = os.path.join(absDirPath, record.id)
        code = XmlStorage.recordToSource(record)
        open(path, 'w').write(code)
        paths.append(path)

        # create a git commit
        XmlStorage.git.commit(paths, commitMsg)

    @staticmethod
    def genId(timestamp):
        """ Generate a record id base on the timestamp
        and some random data, the result is a sha1 sum.
        """
        import hashlib
        length = 1024
        ranData = open('/dev/urandom', 'rb').read(length)
        string = str(timestamp).encode() + ranData
        return hashlib.sha1(string).hexdigest()

    @staticmethod
    def allIds():
        """ Return a generator which yields IDs of all log records.
        """
        dataDir = XmlStorage.dataDir
        cmd = ['find', dataDir, '-name', '.git',
               '-prune', '-o', '-type', 'f', '-print0']
        res = applib.get_status_byte_output(cmd)
        if not res[0]:
            print('find command failed:', file=sys.stderr)
            print(res[2].decode(), file=sys.stderr, end='')
            return

        lines = res[1].split(b'\x00')[:-1]   # remove the last empty one
        for path in lines:
            yield os.path.basename(path.decode())

    @staticmethod
    def __delete(id, path=None):
        """ Delete a record, either by id or by path
        """
        if not path:
            path = XmlStorage.idToPath(id)
        os.unlink(path)

    @staticmethod
    def delete(ids, preAction=(lambda x:False), postAction=(lambda x:0)):
        """ Delete multiple records, create a commit
        """
        paths = list(map(XmlStorage.idToPath, ids))
        deletedPaths  = []
        deletedBNames = []
        for path in paths:
            record = XmlStorage.load(None, path)
            if not preAction(record):
                continue
            XmlStorage.__delete(None, path)
            postAction(record)
            deletedPaths.append(path)
            deletedBNames.append(record.id)
        if deletedPaths:
            message = 'Delete log\n\n%s' % '\n'.join(deletedBNames)
            XmlStorage.git.commit(deletedPaths, message)

    @staticmethod
    def lastLog():
        """ Fetch the last added/changed log record
        """
        logs = XmlStorage.lastLogs()
        if logs:
            return logs[0]
        else:
            return None

    @staticmethod
    def lastLogs(count=1):
        """ Fetch the last 'count' logs record

        The paths returned by the git.last may contain
        paths that been deleted, it shall be ignored.

        When a single record was collected multiple times,
        the redundant shall be removed.  It can happen
        when the record was changed multiple times (maybe
        plus added action) within the range.
        """
        vCount = count
        while True:
            ps = XmlStorage.git.last(vCount)
            if len(set(ps)) == count:
                break
            else:
                vCount += 1
        paths = []
        for p in ps:
            if p not in paths:
                paths.append(p)
        records = []
        for path in paths:
            path = os.path.join(XmlStorage.dataDir, path)
            if os.path.exists(path):
                record = XmlStorage.load(None, path=path)
                records.append(record)
        return records

    @staticmethod
    def makeFilter(timePoints, regexps, allMatch=False):
        """ Create a filter function for filtering
        the record with the given regular expression,
        and the time points. The filter function
        expects a Record instance object.
        """
        def logFilter(record, regexps=regexps,
                    timePoints=timePoints, allMatch=allMatch):
            """ timeMatch is True if the time of the record is
            within any pair of the timePoints, regMatch is True
            if any of these fields of a record match the given
            regular expression: subject, scene, people, tag,
            and data if it's not of binary form. Return True
            only when both timeMatch and regMatch are True.
            """
            timeMatch = regMatch = True
            # match time
            if timePoints:
                t = record.time
                x = [True for t1, t2 in timePoints if t1 <= t <= t2]
                timeMatch = bool(x)

            # match regular expressions
            if regexps:
                texts = [record.author, record.subject, record.scene,
                         record.people, record.tag]
                if not record.binary:
                    texts.append(record.data)

                if allMatch:
                    def matcher(patterns, inTexts, record):
                        for pat, flag, field in patterns:
                            if field:   # match on a specific field
                                texts = [getattr(record, field)]
                            else:       # match on input fields
                                texts = inTexts
                            match = False
                            for text in texts:
                                # if the pattern matches any of
                                # the text, the pattern is match
                                if re.search(pat, text, flag):
                                    match = True
                                    break
                            # if any pattern is not match
                            # the whole failed.
                            if not match:
                                return False
                        return True
                else:
                    def matcher(patterns, inTexts, record):
                        for pat, flag, field in patterns:
                            if field:   # match on a specific field
                                texts = [getattr(record, field)]
                            else:       # match on input fields
                                texts = inTexts
                            match = False
                            for text in texts:
                                # if the pattern matches any of
                                # the text, the pattern is match
                                if re.search(pat, text, flag):
                                    match = True
                                    break
                            # if any pattern is match,
                            # the whole is match.
                            if match:
                                return True
                        return False
                regMatch = matcher(regexps, texts, record)
            return timeMatch and regMatch

        return logFilter


    @staticmethod
    def searchLogs(fields, criteria, order=None):
        """ Walk through all log records, collect those
        that match the criteria. Return a generator which
        yields a dict for all requested fields.
        """
        def sortRecords(by, records, reverse=False):
            key = lambda record: getattr(record, by)
            records.sort(key=key, reverse=reverse)

        def transRecords(records, fields):
            for r in records:
                d = dict([i for i in r.elements().items() if i[0] in fields])
                yield d

        # do a git assisted search if the limit is the only criteria
        if criteria.get('limit'):
            ids   = criteria.get('ids')
            times = criteria.get('times')
            regxs = criteria.get('regxs')
            patns = regxs.get('patterns') if regxs else None
            if not times and not patns and not ids:
                records = XmlStorage.lastLogs(criteria['limit'])
                if order:
                    sortRecords(order['by'], records, reverse=(not order['ascending']))
                return transRecords(records, fields)

        # create the filter function
        if criteria and (criteria.get('times') or criteria.get('regxs')):
            times = criteria.get('times', [])
            regxs = criteria.get('regxs')
            allMatch = regxs.get('allMatch', False) if regxs else False
            patterns = regxs.get('patterns') if regxs else None
            filter = XmlStorage.makeFilter(times, patterns, allMatch)
        else:
            filter = lambda record: True

        # the IDs
        ids = criteria.get('ids')
        if not ids:
            ids = Record.allIds()
        else:
            completeIds = []
            for id in ids:
                completeIds.extend(XmlStorage.matchId(id))
            ids = completeIds

        # collect the records
        records = []
        for id in ids:
            x = Record.load(id)
            if not x:
                continue
            if filter(x):
                records.append(x)
        if order:
            sortRecords(order['by'], records, reverse=(not order['ascending']))
        return transRecords(records, fields)
