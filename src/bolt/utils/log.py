import logging
import sys
import os
import time
import typing
import io
import tempfile

from bolt.utils.config import Config, ConfigConstants

formatter = logging.Formatter("[%(levelname)s] %(asctime)s : %(message)s",
                              datefmt="%H:%M:%S")

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

app_name = Config.get(ConfigConstants.AppName)
app_log_file = os.getenv(f"{app_name.upper()}_LOG_FILE")

if app_log_file is None:
    temp_dir = tempfile.gettempdir()
    app_log_file = f"{temp_dir}/{app_name}_log.txt"

file_handler = logging.FileHandler(filename=app_log_file)
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

if sys.stdout is not None:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

def _list_fmt(l: typing.List) -> str:
    if not isinstance(l, list):
        return str(l)

    buffer = io.StringIO()
    buffer.write("[\n")
    buffer.write(",\n".join([f"{' ' * 4}{str(item)}" for item in l]))
    buffer.write("\n]")

    return buffer.getvalue()

def _dict_fmt(d: typing.Dict) -> str:
    if not isinstance(d, dict):
        return str(d)
    
    buffer = io.StringIO()
    buffer.write("{\n")
    buffer.write(",\n".join([f"{' ' * 4}{str(key)} : {str(value)}" for key, value in d.items()]))
    buffer.write("\n}")
    
    return buffer.getvalue()

_FMT_FUNCS = {
    list: _list_fmt,
    dict: _dict_fmt,
    None: str
}

def _fmt(obj: typing.Any) -> str:
    try:
        func = _FMT_FUNCS.get(type(obj))

        return func(obj)
    except:
        return str(obj)

def _args_fmt(*args) -> str:
    return _fmt(args[0]).strip("\n") if len(args) == 1 else ", ".join([_fmt(arg) for arg in args]).strip("\n")

def debug(*args):
    logging.debug(_args_fmt(*args))

def info(*args):
    logging.info(_args_fmt(*args))

def warning(*args):
    logging.warning(_args_fmt(*args))

def error(*args):
    logging.error(_args_fmt(*args))

def critical(*args):
    logging.critical(_args_fmt(*args))
