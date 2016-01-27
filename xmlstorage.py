from logrecord import LogRecord
import timeutils

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
    def load(path):
        """ Load the content of the path,
        parse it, and return a record instance.
        """
        try:
            code = open(path).read()
            doc  = XmlStorage.sourceToDom(code)
        except:
            return None
        fields = {}
        for node in doc.firstChild.childNodes:
            if node.nodeType == node.ELEMENT_NODE:
                name = node.localName
                textNode = node.firstChild
                data = textNode.data if textNode else ''
                fields[name] = data
        fields['binary'] = True if fields['binary'] == 'true' else False
        fields['path'] = path
        return LogRecord(**fields)

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
        XmlStorage.createNode(root, "subject", record.subject)
        XmlStorage.createNode(root, "author", record.author)
        XmlStorage.createNode(root, "time", timeutils.isodatetime(record.time))
        XmlStorage.createNode(root, "scene", record.scene)
        XmlStorage.createNode(root, "people", record.people)
        XmlStorage.createNode(root, "tag", record.tag)
        if record.binary:
            XmlStorage.createNode(root, "binary", "true")
        else:
            XmlStorage.createNode(root, "binary", "false")
        XmlStorage.createNode(root, "data", record.data)
        xmlCode = doc.toprettyxml()
        xmlCode = re.sub('\t', '    ', xmlCode)     # replace tabs with spaces
        return xmlCode

    @staticmethod
    def save(record, path):
        """ Convert the record to Xml code,
        and Write the code to the path.
        """
        code = XmlStorage.recordToSource(record)
        open(path, 'w').write(code)
