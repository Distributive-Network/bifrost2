"""
Job Filesystem.

A vfsystem to be used for dcp jobs via tar vfs.

Note: Currently only supported in the Pyodide worktime.

Author: Will Pringle <will@distributive.network>
Date: July 2024
"""
import pathlib
import tarfile
import os

import readline
import atexit
import rlcompleter

class JobFS:
    """Job Virtual Filesystem (JobFS)."""
    def add(self, local_src, vfs_dest=None):
        """Adds local file[s] to the vfs.
        If dest not specified, add file from root.
        local_src can be of type:
            - string        : filename
            - pathlib.Path  : filename
        """
        if vfs_dest is None:
            vfs_dest = os.path.join(self.home, os.path.basename(local_src))
        vfs_dest = self._resolve_path(vfs_dest)

        if os.path.isdir(local_src):
            self.mkdir(vfs_dest)
            dir_list = os.listdir(local_src)
            for sub_path in dir_list:
                self.add(os.path.join(local_src, sub_path), os.path.join(vfs_dest, sub_path))
        else:
            with open(local_src, 'rb') as f:
                content = f.read()

            self.vfs[vfs_dest] = content

    def chdir(self, vfs_dest):
        """Change directory."""
        vfs_dest = self._resolve_path(vfs_dest)
        self.cwd = vfs_dest

    def __init__(self):
        self.vfs = {}
        self.vfs['/'] = self.vfs
        self.home = '/home/pyodide'
        self.mkdir(self.home)
        self.cwd = self.home

    def _resolve_path(self, path):
        if path.startswith('~'):
            path = path.replace('~', self.home, 1)
        if not path.startswith('/'):
            path = os.path.join(self.cwd, path)
        return os.path.normpath(path)

    def serialize(self):
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            for path, content in self.vfs.items():
                file_info = tarfile.TarInfo(name=path.lstrip('/'))
                file_info.size = len(content)
                tar.addfile(file_info, io.BytesIO(content))
        tar_stream.seek(0)
        return tar_stream

    def mkdir(self, new_dir):
        new_dir = self._resolve_path(new_dir)
        parts = pathlib.Path(new_dir).parts
        prev_inode = self.vfs
        for part in parts:
            if part not in prev_inode:
                prev_inode[part] = {}
            prev_inode = prev_inode[part]

    def cd(self, *args):
        return self.chdir(*args)

    def tree(self):
        return str(self.vfs)

    def ls(self):
        parts = pathlib.Path(self.cwd).parts
        dir_node = self.vfs
        for part in parts:
            dir_node = dir_node[part]
        return list(dir_node.keys())

    def _repl(self):
        """Repl for debugging a JobFS vfs."""
        completions = [attr for attr in dir(self) if not attr.startswith('_')] + ['clear', 'exit']
        def get_completions():
            return completions + self.ls()
        readline.set_completer(lambda text, state: [c for c in completions + self.ls() if c.startswith(text)][state])
        readline.parse_and_bind("tab: complete")

        while True:
            try:
                # Read
                user_input = input(f"{self.cwd} > ")
                args = user_input.split(" ")
                
                # If the user types 'exit' or 'quit', exit the REPL
                if user_input in ('exit', 'quit'):
                    print("Exiting REPL...")
                    break
                elif user_input == '':
                    result = None
                elif user_input == 'clear':
                    os.system('clear')
                    result = None
                elif hasattr(self, args[0]):
                    fn = getattr(self, args[0])
                    del args[0]
                    if callable(fn):
                        result = fn(*args)
                    else:
                        result = str(fn)
                else:
                    result = eval(user_input)
                if result is not None:
                    print(result)
            
            except Exception as e:
                print(f"Error: {e}")
 
print("-------\n")
jfs = JobFS()
jfs._repl()
