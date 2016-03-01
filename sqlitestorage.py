import os
from record import Record
from timeutils import isodatetime
import applib
import sqlite3

class E:
    """ sqlite3 storage engine for the record
    """
    recordTbl = 'record'
    orderBy   = 'mtime'
    orderHow  = 'desc'

    @staticmethod
    def setup(dataDir):
        engineDir = os.path.join(dataDir, 'sqlite3')
        os.makedirs(engineDir, exist_ok=True)
        dbPath    = os.path.join(engineDir, 'db.sqlite3')
        E.conn    = sqlite3.connect(dbPath)
        E.fields  = list(Record.fields.keys())
        E.createTables(E.conn)

    @staticmethod
    def createTables(conn):
        cur = conn.cursor()
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % E.recordTbl
        if cur.execute(sql).fetchone():
            return
        cur.execute('begin')
        sql = 'CREATE TABLE IF NOT EXISTS record (_id INTEGER PRIMARY KEY AUTOINCREMENT, id CHAR(40) NOT NULL, subject TEXT NOT NULL, author TEXT NOT NULL, time DATETIME NOT NULL, mtime DATETIME NOT NULL, scene TEXT, people TEXT, tag TEXT, data BLOB, binary TINYINT NOT NULL)'
        cur.execute(sql)
        cur.execute('CREATE INDEX record_id_idx ON record (id)')
        cur.execute('CREATE INDEX record_time_idx ON record (time)')
        cur.execute('CREATE INDEX record_mtime_idx ON record (mtime)')
        conn.commit()

    @staticmethod
    def commit():
        """ Do a database transaction commit
        """
        E.conn.commit()

    @staticmethod
    def rollback():
        """ Do a database transaction rollback
        """
        E.conn.rollback()

    @staticmethod
    def load(id):
        """ Load the content of the record from disk,
        parse it, and return a record instance.
        """
        fields = ','.join(E.fields)
        table  = E.recordTbl
        sql    = 'SELECT %s FROM %s WHERE id LIKE ?' % (fields, table)
        cur    = E.conn.cursor()
        cur.execute(sql, ['%%%s%%' % id])
        elements = cur.fetchall()
        if elements:
            record = E._elements_to_record(E.fields, elements[0])
        else:
            record = None
        return record

    @staticmethod
    def matchId(id):
        """ Return all IDs that starts with 'id'
        """
        table = E.recordTbl
        sql   = 'select id from %s where id like ?' % table
        val   = [id + '%']
        cur   = E.conn.cursor()
        cur.execute(sql, val)
        ids   = cur.fetchall()
        ids   = [x[0] for x in ids]
        return ids

    @staticmethod
    def save(record, oldRecord=None, commit=True):
        """ For add and change a record.
        If the oldRecord is provided, this is to change
        an existing record, else it's to add a new one.
        if 'commit' is True, do a commit to the db.
        """
        tbl  = E.recordTbl
        data = dict(record.elements()).items()
        data = Record.convertFields(data, False)
        if not oldRecord:   # add new record
            record.id  = applib.genId(record.time)
            data['id'] = record.id
            # insert
            flds = ','.join(E.fields)
            hlds = ','.join(['?'] * len(E.fields))
            vals = [data[k] for k in E.fields]
            sql  = 'INSERT INTO %s (%s) VALUES (%s)' % (tbl, flds, hlds)
        else:
            if record == oldRecord:
                return
            # update
            keys = []
            for k in E.fields:
                vnew = getattr(record, k)
                vold = getattr(oldRecord, k)
                if vnew != vold:
                    keys.append(k)
            vals = [data[k] for k in keys]
            pairs = ','.join(['%s=?'] * len(keys)) % tuple(keys)
            sql = 'UPDATE %s SET %s WHERE id = ?' % (tbl, pairs)
            vals.append(record.id)
        try:
            cur = E.conn.cursor()
            cur.execute('begin')
            cur.execute(sql, vals)
            if commit:
                E.commit()
            return record
        except:
            return None

    @staticmethod
    def allIds():
        """ Return a generator which yields IDs of all log records.
        """
        table = E.recordTbl
        sql   = 'select id from %s' % table
        cur   = E.conn.cursor()
        cur.execute(sql)
        for (id,) in cur:
            yield id

    @staticmethod
    def delete(ids, preAction=(lambda x:False), postAction=(lambda x:0), commit=True):
        """ Delete multiple records
        """
        sql = 'DELETE from %s WHERE id = ?' % E.recordTbl
        try:
            cur = E.conn.cursor()
            cur.execute('begin')
            for id in ids:
                record = SqliteStorage.load(id)
                if not preAction(record):
                    continue
                cur.execute(sql, [id])
                postAction(record)
            if commit:
                E.commit()
            return True
        except:
            return False

    @staticmethod
    def lastLog():
        """ Fetch the last added/changed log record
        """
        logs = E.lastLogs()
        if logs:
            return logs[0]
        else:
            return None

    @staticmethod
    def _elements_to_record(fields, elements):
        """ Convert an iterable of record
        fields data, into a record instance,
        the fields and elements shall match
        in order.
        """
        D = Record.convertFields(zip(fields, elements))
        return Record(**D)

    @staticmethod
    def lastLogs(count=1):
        """ Fetch the last 'count' logs record
        """
        records  = []
        fields   = ','.join(E.fields)
        table    = E.recordTbl
        orderBy  = E.orderBy
        orderHow = E.orderHow
        sql = 'SELECT %s FROM %s ORDER BY %s %s LIMIT %s'
        sql = sql % (fields, table, orderBy, orderHow, count)
        cur = E.conn.cursor()
        cur.execute(sql)
        records_elements = cur.fetchall()
        for elements in records_elements:
            record = E._elements_to_record(E.fields, elements)
            records.append(record)
        return records

    @staticmethod
    def procTimeAndRe(criteria):
        """ Parse the criteria, produce the SQL and the Values
        time points in the criteria are unix timestamps, they
        must be converted to text format to suit the SQL needs.
        """
        whereSql  = ''
        whereVals = []

        times    = criteria.get('times')
        tmField  = times.get('field') if times else None
        tmPoints = times.get('points', []) if times else []
        tmPoints = [(isodatetime(t1), isodatetime(t2)) for t1, t2 in tmPoints]
        regxs    = criteria.get('regxs')
        allMatch = regxs.get('allMatch', False) if regxs else False
        patterns = regxs.get('patterns') if regxs else []

        # time matching SQL
        tmSqls = []
        tmVals = []
        for t1, t2 in tmPoints:
            tmSqls.append('(? <= %s AND %s <= ?)' % (tmField, tmField))
            tmVals.extend([t1, t2])
        tmSqls = ' OR '.join(tmSqls)

        # the regular expression matching SQL (LIKE for now )
        # unfortunately, Python sqlites module seems not support RE
        # we use LIKE operator instead, temporarily.
        matchSqls = []
        matchVals = []
        texts = ['author', 'subject', 'scene', 'people', 'tag']
        for pat, flag, field in patterns:
            """ one pattern against all texts,
            or a specific field.
            """
            pat = '%%%s%%' % pat    # A 'in' LIKE
            if field:
                matchSqls.append('%s LIKE ?' % field)
                matchVals.append(pat)
            else:
                ss = ['%s LIKE ?' % x for x in texts]
                ss.append('(binary = 0 AND data LIKE ?)')
                ss = ' OR '.join(ss)
                matchSqls.append('(%s)' % ss)
                matchVals.extend([pat] * (len(texts) + 1))
        if allMatch:
            matchSqls = ' AND '.join(matchSqls)
        else:
            matchSqls = ' OR '.join(matchSqls)

        subSqls = []
        if tmSqls:
            subSqls.append('(%s)' % tmSqls)
            whereVals.extend(tmVals)
        if matchSqls:
            subSqls.append('(%s)' % matchSqls)
            whereVals.extend(matchVals)
        whereSql = ' AND '.join(subSqls)

        return whereSql, whereVals

    @staticmethod
    def searchLogs(fields, criteria, order=None):
        """ Collect records that match the criteria. Only
        collect fields that in 'fields', return a generator
        which yields a dict for all requested fields.
        """
        whereSql  = ''
        whereVals = []
        # the WHERE clause
        ids = criteria.get('ids')
        if ids:
            ss = ' OR '.join(['id LIKE ?'] * len(ids))
            whereSql  = '(%s)' % ss
            whereVals = ['%%%s%%' % id for id in ids]
        elif criteria and (criteria.get('times') or criteria.get('regxs')):
            whereSql, whereVals = E.procTimeAndRe(criteria)

        # construct a complete SQL
        table = E.recordTbl
        sql   = 'SELECT %s FROM %s' % (','.join(fields), table)
        vals  = []
        if whereSql:
            sql += ' WHERE %s' % whereSql
            vals.extend(whereVals)
        if order:
            orderBy  = order['by']
            orderHow = 'ASC' if order['ascending'] else 'DESC'
        else:
            # apply the default order
            orderBy  = E.orderBy
            orderHow = E.orderHow
        orderSql = ' ORDER BY %s %s' % (orderBy, orderHow)
        sql += orderSql
        if criteria.get('limit'):
            sql += ' LIMIT %s' % criteria.get('limit')

        cur    = E.conn.cursor()
        cur.execute(sql, vals)
        allElements = cur.fetchall()
        for elements in allElements:
            D = Record.convertFields(zip(fields, elements))
            yield D

SqliteStorage = E
