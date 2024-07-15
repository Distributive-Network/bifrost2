import subprocess
import sys
import shutil

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
    execute(f"cd {package_json_location} && {node_package_manager} i --no-package-lock") # do not update package-lock.json

if __name__ == "__main__":
    main()

