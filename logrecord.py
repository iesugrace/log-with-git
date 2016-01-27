import os
from record import Record
import timeutils

class LogRecord(Record):
    """ Log Record capable of Git operations
    OS aware operations defined here.
    """
    def save(self, dataDir, fileName=None):
        """ Save instance data to disk
        """
        timestamp  =  self.time
        dateEle    =  timeutils.isodate(timestamp).split('-')
        absDirPath =  os.path.join(dataDir, *dateEle)
        if not fileName:
            fileName = self.genName(timestamp)
        filePath   =  os.path.join(absDirPath, fileName)
        os.makedirs(absDirPath, exist_ok=True)
        self.engine.save(self, filePath)
        return filePath

    def genName(self, timestamp):
        """ Generate a file name base on the timestamp,
        and some random data, the result is a sha1 sum.
        """
        import hashlib
        length = 1024
        ranData = open('/dev/urandom', 'rb').read(length)
        string = str(timestamp).encode() + ranData
        return hashlib.sha1(string).hexdigest()

    @staticmethod
    def load(path):
        return LogRecord.engine.load(path)
