import unittest
import asyncio
import tempfile
import tarfile
import os
import uuid
import pythonmonkey as pm
import dcp
dcp.init()

def write_to_tar(jfs):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz', prefix='bf2-tar-') as temp_file:
        file_path = temp_file.name
        temp_file.write(jfs.to_gzip_tar())
    return file_path


def uncompress_tar(tar_path):
    tempdir = tempfile.mkdtemp(prefix='bf2-dir-')
    with tarfile.open(tar_path, 'r:gz') as tar:
        for member in tar.getmembers():
            original_path = member.name
            adjusted_path = os.path.join(tempdir, member.name.lstrip('/'))

            if not adjusted_path.startswith(tempdir):
                raise Exception(f"Attempted to extract outside of target directory: {adjusted_path}")

            if member.isdir():
                os.makedirs(adjusted_path, exist_ok=True)
            else:
                parent_dir = os.path.dirname(adjusted_path)
                os.makedirs(parent_dir, exist_ok=True)
                with tar.extractfile(member) as source, open(adjusted_path, 'wb') as target:
                    target.write(source.read())
            #print(f"Extracted {original_path} to {adjusted_path}")

    return tempdir


def get_files_in_dir(dirpath):
    path_files = {}
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path) as f:
                file_path = file_path.replace(dirpath, '')
                path_files[str(file_path)] = f.read()
    return path_files


def resolve_path(path, cwd):
    home_dir = '/home/pyodide'
    if path.startswith('~'):
        path = path.replace('~', home_dir, 1)
    if not path.startswith('/'):
        path = os.path.join(cwd, path)
    return os.path.normpath(path)


def adder(files_to_add, job_fs):
    files_expect_output = []

    for file in files_to_add:
        text = uuid.uuid4().hex.upper()
        job_fs.chdir(file['cwd'])
        job_fs.add(bytes(text, 'utf-8'), file['path'])
        abs_path = resolve_path(file['path'], file['cwd'])
        files_expect_output.append({ 'content': text, 'abs_path': abs_path })

    return files_expect_output


class TestJobFS(unittest.TestCase):

    def test_smoke_job_fs(self):
        """Simple smoke test."""
        self.assertTrue(dcp.JobFS is not None)
        new_fs = dcp.JobFS()
        self.assertTrue(dcp.JobFS.add is not None)
        self.assertTrue(dcp.JobFS.chdir is not None)

    def test_add_bytes_relative(self):
        """Test adding bytes relative from differnt places."""
        new_fs = dcp.JobFS()

        test_files_to_add = [
            { 'cwd': '/home/pyodide', 'path': 'relative-01' },
            { 'cwd': '/home/pyodide', 'path': './relative-02' },
            { 'cwd': '/home/pyodide', 'path': '../relative-03' },
            { 'cwd': '/home/pyodide', 'path': '../../relative-04' },
            { 'cwd': '/', 'path': 'relative-05' },
            { 'cwd': '/', 'path': './relative-06' },
            { 'cwd': '/', 'path': './home/relative-07' },
            { 'cwd': '/', 'path': './home/pyodide/relative-08' },
            { 'cwd': '/', 'path': '../../../../../../../relative-09' },
            { 'cwd': '/', 'path': '../home/pyodide/../../home/relative-10' },
            { 'cwd': '/home', 'path': '/home/pyodide/new_dir_01/absolute_path.txt' },
        ]

        expected_files = adder(test_files_to_add, new_fs)
        tar_filename = write_to_tar(new_fs)
        dir_path = uncompress_tar(tar_filename)
        real_files = get_files_in_dir(dir_path)

        for file in expected_files:
            real_file = real_files[file['abs_path']]
            self.assertEqual(file['content'], real_file)

    def test_add_bytes_chdir_add(self):
        """Testing adding relative files from different working directories."""
        new_fs = dcp.JobFS()

        test_files_to_add = [
            { 'cwd': '.', 'path': 'slash-home-pyodide---01' , 'abs_path_prefix': '/home/pyodide/' },
            { 'cwd': '..', 'path': 'slash-home---02', 'abs_path_prefix': '/home/' },
            { 'cwd': '/home/pyodide', 'path': 'slash-home-pyodide---03' , 'abs_path_prefix': '/home/pyodide/' },
            { 'cwd': '../../', 'path': 'slash---04', 'abs_path_prefix': '/' },
            { 'cwd': '/home', 'path': 'slash-home---05', 'abs_path_prefix': '/home/' },
            { 'cwd': '..', 'path': 'slash---06', 'abs_path_prefix': '/' },
            { 'cwd': '../../../../../../', 'path': 'slash---07', 'abs_path_prefix': '/' },
        ]

        expected_files = adder(test_files_to_add, new_fs)
        tar_filename = write_to_tar(new_fs)
        dir_path = uncompress_tar(tar_filename)
        real_files = get_files_in_dir(dir_path)

        for i in range(len(test_files_to_add)):
            abs_path = test_files_to_add[i]['abs_path_prefix'] + test_files_to_add[i]['path']
            expected_file = expected_files[i]
            self.assertEqual(real_files[abs_path], expected_file['content'])


    def test_add_file_absolute(self):
        """Testing adding a file using an absolute path for the job_fs vfs destination."""
        new_fs = dcp.JobFS()
        vfs_dest = '/i/put/the/lorem/ipsum/file/here.txt'
        lorem_ipsum = 'Lorem ipsum dolor sit amet,\nconsectetur epicness.'

        with tempfile.NamedTemporaryFile(delete=False, prefix='bf2-test-') as temp_file:
            file_path = temp_file.name
            temp_file.write(bytes(lorem_ipsum, 'utf-8'))

        new_fs.add(file_path, vfs_dest)

        tar_filename = write_to_tar(new_fs)
        dir_path = uncompress_tar(tar_filename)
        real_files = get_files_in_dir(dir_path)

        self.assertEqual(real_files[vfs_dest], lorem_ipsum)


    def test_add_dir(self):
        """TODO: should probably test nested directories."""
        new_fs = dcp.JobFS()
        vfs_dest = '/home/pyodide/files'

        print("-------------------------------------")

        tempdir = tempfile.mkdtemp(prefix='bf2-dir-')
        expected_files = {}

        # write a bunch of files within the directory
        for i in range(10):
            with tempfile.NamedTemporaryFile(delete=False, prefix=f'file-{i}', dir=tempdir) as temp_file:
                file_path = temp_file.name
                text = f'this is the {i}th file'
                expected_files[vfs_dest + '/' + os.path.basename(temp_file.name)] = text
                temp_file.write(bytes(text, 'utf-8'))

        # add whole directory
        new_fs.add(tempdir, vfs_dest)

        tar_filename = write_to_tar(new_fs)
        dir_path = uncompress_tar(tar_filename)
        real_files = get_files_in_dir(dir_path)

        for file in expected_files:
            self.assertEqual(expected_files[file], real_files[file])


if __name__ == '__main__':
    unittest.main()

