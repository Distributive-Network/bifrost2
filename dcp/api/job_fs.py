"""
Job Filesystem.

A vfsystem to be used for dcp jobs via tar vfs.

Note: Currently only supported in the Pyodide worktime.
Note: This logic will be mostly replaced by dcp-client's JobFS when it lands.

Author: Will Pringle <will@distributive.network>
Date: July 2024
"""
import pathlib
import tarfile
import os
import io

import readline
import atexit
import rlcompleter

class JobFS:
    """Job Virtual Filesystem (JobFS)."""
    def __init__(self):
        self.vfs = {}
        self.vfs['/'] = self.vfs
        self.home = '/home/pyodide'
        self.mkdir(self.home)
        self.cwd = self.home

    def add(self, local_src, vfs_dest=None):
        """Adds local file[s] to the vfs.
        If dest not specified, add file from current working directory.
        Overwrites file if there is already one specified there.
        local_src can be of type:
            - string        : file path 
            - pathlib.Path  : file path
            - bytes         : data blob
            - bytearray     : data blob
            - file-like     : data blob
        vfs_dest can be of type:
            - string        : file path (optional)
            - pathlib.Path  : file path (optional)
        vfs_dest is not optional when passing data blobs.
        """
        if isinstance(local_src, io.IOBase):
            local_src = local_src.read()

        if isinstance(local_src, bytes) or isinstance(local_src, bytearray):
            if vfs_dest is None:
                raise Exception('Must specify a destination file path to write to')
        elif isinstance(local_src, str) or isinstance(local_src, pathlib.PurePath):
            if vfs_dest is None:
                vfs_dest = os.path.basename(local_src)
            local_src = str(local_src)

        vfs_dest = self._resolve_path(vfs_dest)

        # build up path along the way if not present
        dest_parts = list(pathlib.Path(vfs_dest).parts)
        built_parts = '/'
        new_filename = dest_parts.pop()
        for part in dest_parts:
            built_parts = os.path.join(built_parts, part)
            self.mkdir(built_parts)

        parent_dirnode = self._path_to_dir_node(built_parts)

        if isinstance(local_src, bytes) or isinstance(local_src, bytearray):
            parent_dirnode[new_filename] = local_src
        elif os.path.isdir(local_src):
            self.mkdir(vfs_dest)
            dir_list = os.listdir(local_src)
            for sub_path in dir_list:
                self.add(os.path.join(local_src, sub_path), os.path.join(vfs_dest, sub_path))
        else:
            with open(local_src, 'rb') as f:
                content = f.read()
            parent_dirnode[new_filename] = content

    def chdir(self, vfs_dest):
        """Change directory."""
        vfs_dest = self._resolve_path(vfs_dest)
        if self._path_to_dir_node(vfs_dest) is None:
            raise self.InvalidPath(vfs_dest)
        self.cwd = vfs_dest


    def _resolve_path(self, path):
        if path.startswith('~'):
            path = path.replace('~', self.home, 1)
        if not path.startswith('/'):
            path = os.path.join(self.cwd, path)
        return os.path.normpath(path)

    def _path_to_dir_node(self, path):
        dirnode = self.vfs
        parts = pathlib.Path(path).parts
        for part in parts:
            if part not in dirnode:
                return None
            dirnode = dirnode[part]
        return dirnode

    def _flatten_vfs(self, dirnode=None, path_so_far='/'):
        if dirnode is None:
            dirnode = self.vfs
        files = []
        for key in list(dirnode.keys()):
            if key == '/':
                continue
            if isinstance(dirnode[key], dict):
                files.append((os.path.join(path_so_far, key), None))
                files = files + self._flatten_vfs(dirnode[key], os.path.join(path_so_far, key))
            else:
                files.append((os.path.join(path_so_far, key), dirnode[key]))
        return files

    def to_gzip_tar(self) -> bytes:
        """Serializes the vfs into a zip-compressed tarball."""
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w:gz') as tar:
            for (file_path, file_content) in self._flatten_vfs():
                tar_info = tarfile.TarInfo(name=file_path)
                if file_content is None:
                    tar_info.type = tarfile.DIRTYPE
                    tar.addfile(tarinfo=tar_info)
                else:
                    file_data = file_content
                    if isinstance(file_content, str):
                        file_data = file_content.encode('utf-8')
                    tar_info.size = len(file_data)
                    tar.addfile(tarinfo=tar_info, fileobj=io.BytesIO(file_data))
        tar_stream.seek(0)
        return tar_stream.read()

    def write_to_file(self, file_path):
        tar_bytes = self.to_gzip_tar()
        with open(file_path, 'wb') as f:
            f.write(tar_bytes)

    def mkdir(self, new_dir):
        """For debugging."""
        new_dir = self._resolve_path(new_dir)
        parts = pathlib.Path(new_dir).parts
        prev_dirnode = self.vfs
        for part in parts:
            if part not in prev_dirnode:
                prev_dirnode[part] = {}
            prev_dirnode = prev_dirnode[part]

    def cd(self, *args):
        """For debugging."""
        return self.chdir(*args)

    def tree(self, dirnode=None, level=0):
        """For debugging."""
        val = ''
        if dirnode is None:
            dirnode = self.vfs
        for key in list(dirnode.keys()):
            if key == '/':
                continue
            val = f"{val}{'  - ' * level}{key}"
            if isinstance(dirnode[key], dict):
                val = f"{val}/\n"
                val = val + self.tree(dirnode[key], level + 1)
            else:
                val = f"{val}\n"
        return val

    def ls(self, dir_to_list=None):
        """For debugging."""
        if dir_to_list is None:
            dir_to_list = self.cwd
        else:
            dir_to_list = self._resolve_path(dir_to_list)
        parts = pathlib.Path(dir_to_list).parts
        dir_node = self.vfs
        for part in parts:
            dir_node = dir_node[part]
        return list(dir_node.keys())

    def cat(self, file_path):
        """For debugging."""
        file_path = self._resolve_path(file_path)
        for (path, content) in self._flatten_vfs():
            if path == file_path:
                return content.decode('utf-8')
        return None

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

    # static property
    class InvalidPath(Exception):
        def __init__(self, path):
            self.message = f"{path} is invalid"
            super().__init__(self.message)

