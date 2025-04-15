import sys
import shutil
import os
import platform
import subprocess
import ctypes
import ctypes.wintypes as wintypes
import hashlib
import typing
from concurrent.futures import ThreadPoolExecutor, as_completed

def clean_path(path: str) -> str:
    return path.replace("\\", "/")

def get_documents_folder():
    """
    """
    if platform.system() == "Windows":
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        ctypes.OleDLL("shell32").SHGetFolderPathW(None, 5, None, 0, buf)

        return buf.value.replace("\\", "/")
    elif platform.system() == "Linux":
        return os.path.expanduser("~/Documents")

def safe_file_copy(src: str,
                 dst: str):
    """
    """
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))

    if not os.path.exists(os.path.dirname(dst)):
        os.makedirs(os.path.dirname(dst))

    shutil.copy2(src, dst)

def safe_dir_copy(src: str,
                  dst: str,
                  mirror: bool = True):
    """
    """
    if not os.path.isdir(src) or not os.path.isdir(dst):
        return

    if platform.system() == "Windows":
        command = []
        command.append("robocopy")
        command.append(src.replace("/", "\\"))
        command.append(dst.replace("/", "\\"))
        command.append("/MT:{}".format(os.cpu_count()))
        command.append("/e")
        command.append("/j")
        command.append("/z")
        command.append("/ns")
        command.append("/nc")
        command.append("/nfl")
        command.append("/ndl")
        command.append("/np")
        command.append("/njh")
        command.append("/njs")

        if mirror:
            command.append("/mir")

        startupInfos = subprocess.STARTUPINFO()
        startupInfos.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupInfos.wShowWindow = 0

        p = subprocess.Popen(command,
                             startupinfo=startupInfos)

        p.wait()
    else:
        raise NotImplementedError("safe_dir_copy() has not been implemented on this platform")

def multithreaded_dir_copy(src: str,
                           dst: str,
                           callbackProgressFunc: typing.Callable = None):
    """
    """
    if not os.path.isdir(src) or not os.path.isdir(dst):
        return

    srcFiles = list()
    dstFiles = list()

    for file in os.listdir(src):
        filePath = os.path.join(src, file)

        if os.path.isfile(filePath):
            dstFilePath = os.path.join(dst, file)

            srcFiles.append(filePath)
            dstFiles.append(dstFilePath)

    progressStep = 100.0 / len(srcFiles)

    progress = 0.0

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
        for done in as_completed([pool.submit(shutil.copy2, *files) for files in zip(srcFiles, dstFiles)]):
            progress += progressStep

            if callbackProgressFunc is not None:
                callbackProgressFunc(progress)

    if callbackProgressFunc is not None:
        callbackProgressFunc(100.0)

def replace_extension(filepath: str,
                      new_extension: str) -> str:
    """
    """
    if not new_extension.startswith("."):
        new_extension = ".{}".format(new_extension)

    return os.path.splitext(filepath)[0] + new_extension


def get_directory_content_hash(directory_path: str):
    """
    """
    if not os.path.exists(directory_path):
        return "0"

    hash = hashlib.md5()

    for root, dirs, files in os.walk(directory_path):
        for file in files:
            filePath = os.path.join(root, file)

            mtime = os.path.getmtime(filePath)

            hash.update("{}".format(mtime).encode("utf-8"))

    return hash.hexdigest()

def safe_rmdir(directory_path: str):
    """
    """
    if os.path.exists(directory_path):
        subprocess.run(["rmdir", "/s", "/q", directory_path],
                    shell=True)

def safe_directory_clean(directory_path: str):
    """
    """
    for entry in os.scandir(directory_path):
        if entry.is_dir() and not entry.is_symlink():
            subprocess.run(["rmdir", "/s", "/q", entry.path],
                           shell=True)
        else:
            os.remove(entry.path)

def is_executable() -> bool:
    return "python" not in sys.executable