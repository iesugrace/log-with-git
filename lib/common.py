import os, shlex
import tempfile, subprocess

def editContent(content=None):
    """ Edit the content with vi editor, the input
    'content' is byte, the returned one is byte also
    """
    tmpfile = tempfile.NamedTemporaryFile(delete=False)
    if content:
        tmpfile.write(content)
        tmpfile.flush()
    cmd = 'vi ' + tmpfile.name
    p = subprocess.Popen(shlex.split(cmd))
    p.communicate()
    p.wait()
    tmpfile.seek(0)
    content = tmpfile.read()
    os.unlink(tmpfile.name)
    return content
