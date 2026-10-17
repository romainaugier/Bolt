from __future__ import annotations

import glob
import os
import shutil

from bolt.core.errors import CookError
from bolt.core.evaluation import CookContext
from bolt.core.node import Node
from bolt.core.plugs import Input, Output, Parameter


class ListDirectory(Node):
    type_name = "files.list_directory"
    ui = {"icon": "folder_copy"}
    category = "Files"
    description = "Lists the entries of a directory matching a glob pattern, sorted by name."
    always_cook = True
    inputs = (Input("directory", "path"),)
    parameters = (Parameter("pattern", "string", "*"),
                  Parameter("recursive", "bool", False),
                  Parameter("files", "bool", True),
                  Parameter("directories", "bool", False))
    outputs = (Output("paths", "list"),)

    def cook(self, ctx: CookContext) -> None:
        directory = ctx.get("directory")

        if not os.path.isdir(directory):
            raise CookError(f"directory '{directory}' does not exist")

        recursive = ctx.get("recursive")
        pattern = os.path.join(glob.escape(directory), "**" if recursive else "", ctx.get("pattern"))
        include_files = ctx.get("files")
        include_directories = ctx.get("directories")
        paths = []

        for path in sorted(glob.iglob(pattern, recursive=recursive)):
            if os.path.isdir(path):
                if include_directories:
                    paths.append(path)
            elif include_files:
                paths.append(path)

        ctx.set("paths", paths)


class Exists(Node):
    type_name = "files.exists"
    ui = {"icon": "description"}
    category = "Files"
    always_cook = True
    inputs = (Input("path", "path"),)
    outputs = (Output("exists", "bool"), Output("is_directory", "bool"))

    def cook(self, ctx: CookContext) -> None:
        path = ctx.get("path")
        ctx.set("exists", os.path.exists(path))
        ctx.set("is_directory", os.path.isdir(path))


class JoinPath(Node):
    type_name = "files.join_path"
    ui = {"icon": "link"}
    category = "Files"
    inputs = (Input("directory", "path"),)
    parameters = (Parameter("name", "string"),)
    outputs = (Output("path", "path"),)

    def cook(self, ctx: CookContext) -> None:
        ctx.set("path", os.path.join(ctx.get("directory"), ctx.get("name")))


class MakeDirectory(Node):
    type_name = "files.make_directory"
    ui = {"icon": "create_new_folder"}
    category = "Files"
    inputs = (Input("path", "path"),)
    outputs = (Output("path_out", "path"),)
    passthrough = {"path_out": "path"}

    def cook(self, ctx: CookContext) -> None:
        path = ctx.get("path")
        os.makedirs(path, exist_ok=True)
        ctx.set("path_out", path)


class Copy(Node):
    type_name = "files.copy"
    ui = {"icon": "content_copy"}
    category = "Files"
    description = "Copies a file or a directory tree to a destination."
    inputs = (Input("source", "path", required=True), Input("destination", "path"))
    parameters = (Parameter("overwrite", "bool", True),)
    outputs = (Output("path", "path"),)

    def cook(self, ctx: CookContext) -> None:
        source = ctx.get("source")
        destination = ctx.get("destination")

        if not destination:
            raise CookError("no destination given")

        if not os.path.exists(source):
            raise CookError(f"source '{source}' does not exist")

        if os.path.isdir(source):
            if os.path.exists(destination) and not ctx.get("overwrite"):
                raise CookError(f"destination '{destination}' already exists")

            shutil.copytree(source, destination, dirs_exist_ok=True)
            ctx.set("path", destination)

            return

        if os.path.isdir(destination):
            destination = os.path.join(destination, os.path.basename(source))

        if os.path.exists(destination) and not ctx.get("overwrite"):
            raise CookError(f"destination '{destination}' already exists")

        parent = os.path.dirname(destination)

        if parent:
            os.makedirs(parent, exist_ok=True)

        ctx.set("path", shutil.copy2(source, destination))
