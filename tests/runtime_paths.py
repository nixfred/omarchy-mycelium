"""Portable native-fixture paths and a private, automatically allocated X display."""
from contextlib import contextmanager
from pathlib import Path
import os,select,shutil,subprocess

def omarchy_path():
    executable=shutil.which('omarchy')
    candidates=[]
    if os.environ.get('OMARCHY_PATH'):candidates.append(Path(os.environ['OMARCHY_PATH']))
    if executable:candidates.append(Path(executable).resolve().parent.parent)
    candidates.append(Path('/usr/share/omarchy'))
    for path in candidates:
        if (path/'shell/Commons').is_dir() and (path/'shell/Ui').is_dir():return path
    raise RuntimeError('Set OMARCHY_PATH to an Omarchy checkout or installation with shell imports.')

@contextmanager
def private_x_display(size):
    read_fd,write_fd=os.pipe();process=None
    try:
        process=subprocess.Popen(['Xvfb','-displayfd',str(write_fd),'-screen','0',size+'x24','-nolisten','tcp','-ac'],pass_fds=(write_fd,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        os.close(write_fd);write_fd=None
        if not select.select([read_fd],[],[],5)[0]:raise RuntimeError('Private Xvfb did not become ready')
        number=os.read(read_fd,32).decode().strip()
        if process.poll() is not None or not number.isdecimal():raise RuntimeError('Private Xvfb failed')
        yield ':'+number
    finally:
        os.close(read_fd)
        if write_fd is not None:os.close(write_fd)
        if process is not None:
            if process.poll() is None:process.terminate()
            process.wait(timeout=5)
