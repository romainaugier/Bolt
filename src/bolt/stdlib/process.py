from __future__ import annotations

import os
import queue
import subprocess
import threading

from bolt.core.errors import Cancelled, CookError
from bolt.core.evaluation import CookContext
from bolt.core.node import Node
from bolt.core.plugs import Input, Output, Parameter


def _read_lines(stream, lines: queue.Queue) -> None:
    for line in stream:
        lines.put(line)
    lines.put(None)


class Run(Node):
    type_name = "process.run"
    ui = {"icon": "terminal"}
    category = "Process"
    description = "Runs a program, streams its output to the log and fails on a non-zero exit code if 'check' is set."
    inputs = (Input("arguments", "list"),)
    parameters = (Parameter("command", "list"),
                  Parameter("working_directory", "path"),
                  Parameter("environment", "dict"),
                  Parameter("check", "bool", True))
    outputs = (Output("return_code", "int"), Output("output", "string"))

    def cook(self, ctx: CookContext) -> None:
        command = [str(item) for item in (*ctx.get("command"), *ctx.get("arguments"))]

        if not command:
            raise CookError("no command given")

        environment = dict(os.environ)
        environment.update({key: str(value) for key, value in ctx.get("environment").items()})

        try:
            process = subprocess.Popen(command,
                                       cwd=ctx.get("working_directory") or None,
                                       env=environment,
                                       stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       text=True,
                                       errors="replace")
        except OSError as error:
            raise CookError(f"cannot start {command[0]!r}: {error}") from error

        lines: queue.Queue[str | None] = queue.Queue()
        reader = threading.Thread(target=_read_lines, args=(process.stdout, lines), daemon=True)
        reader.start()
        output: list[str] = []

        try:
            while True:
                try:
                    line = lines.get(timeout=0.1)
                except queue.Empty:
                    ctx.checkpoint()
                    continue

                if line is None:
                    break

                output.append(line)
                ctx.info(line.rstrip("\r\n"))

            return_code = process.wait()
        except Cancelled:
            process.terminate()

            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            raise
        finally:
            reader.join(timeout=1)
            process.stdout.close()

        ctx.set("return_code", return_code)
        ctx.set("output", "".join(output))

        if return_code != 0 and ctx.get("check"):
            raise CookError(f"{command[0]} exited with code {return_code}")
