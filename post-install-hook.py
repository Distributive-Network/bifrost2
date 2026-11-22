import subprocess
import sys
import shutil
import os
import shlex

def execute(cmd: str):
    popen = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT,
        shell = True, text = True )
    for stdout_line in iter(popen.stdout.readline, ""):
        sys.stdout.write(stdout_line)
        sys.stdout.flush()

    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

def main():
    node_package_manager = 'npm'
    package_json_location = 'dcp/js'
    # BIFROST2_DCP_CLIENT: an npm package spec or path of the dcp-client to install instead of package.json's
    dcp_client = os.environ.get('BIFROST2_DCP_CLIENT')
    if dcp_client:
        print(f"Installing dcp-client from BIFROST2_DCP_CLIENT={dcp_client}")
        execute(f"cd {package_json_location} && {node_package_manager} i --no-package-lock --no-save {shlex.quote(dcp_client)}")
    else:
        execute(f"cd {package_json_location} && {node_package_manager} i --no-package-lock") # do not update package-lock.json

if __name__ == "__main__":
    main()

