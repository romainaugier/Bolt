from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from collections.abc import Sequence
from typing import Any

from bolt.core.errors import BoltError
from bolt.core.evaluation import Control, EvaluationStatus
from bolt.core.executors import SerialExecutor, ThreadedExecutor
from bolt.core.graph import Graph
from bolt.core.jobs import EventStream, follow_control_commands
from bolt.core.plugs import PlugKind
from bolt.core.registry import Registry
from bolt.core.serialization import load_graph

exit_failed = 1
exit_cancelled = 130


def _parse_variable(text: str) -> tuple[str, Any]:
    name, separator, value = text.partition("=")

    if not separator or not name:
        raise argparse.ArgumentTypeError(f"expected NAME=VALUE, got {text!r}")

    try:
        return name, json.loads(value)
    except json.JSONDecodeError:
        return name, value


def _make_registry(args: argparse.Namespace) -> Registry:
    registry = Registry()

    if not args.no_stdlib:
        registry.load_plugin("bolt.stdlib")

    for plugin in args.plugins:
        registry.load_plugin(plugin)

    registry.discover_plugins(args.plugin_paths)

    return registry


def _print_value(value: Any) -> None:
    try:
        print(json.dumps(value))
    except TypeError:
        print(repr(value))


def _cook(args: argparse.Namespace) -> int:
    registry = _make_registry(args)
    graph = load_graph(args.graph, registry)
    executor = ThreadedExecutor(args.jobs) if args.jobs and args.jobs > 1 else SerialExecutor()
    control = Control()
    previous_handler = signal.signal(signal.SIGINT, lambda signum, frame: control.cancel())

    if args.control:
        follow_control_commands(control, sys.stdin)

    stream = EventStream(graph, sys.stdout) if args.events else None
    targets = args.targets or None

    if targets is None and args.outputs:
        targets = [reference.partition(".")[0] for reference in args.outputs]

    try:
        result = graph.evaluate(targets, variables=dict(args.variables), executor=executor, control=control,
                                force=args.force)
    finally:
        signal.signal(signal.SIGINT, previous_handler)

        if stream is not None:
            stream.close()

    if stream is not None:
        for reference in args.outputs:
            stream.write({"event": "output", "plug": reference, "value": graph.plug(reference).value})

        return {EvaluationStatus.succeeded: 0, EvaluationStatus.failed: exit_failed}.get(result.status,
                                                                                       exit_cancelled)

    logger = logging.getLogger("bolt")

    if result.status is EvaluationStatus.cancelled:
        logger.warning("evaluation cancelled after %.2fs", result.duration)
        return exit_cancelled

    if result.status is EvaluationStatus.failed:
        for node, error in result.failed.items():
            logger.error("%s failed:\n%s", node.path, error)

        if result.blocked:
            logger.error("not cooked because an upstream node failed: %s", ", ".join(node.path for node in result.blocked))

        return exit_failed

    logger.info("cooked %d node(s) in %.2fs", len(result.cooked), result.duration)

    for reference in args.outputs:
        _print_value(graph.plug(reference).value)

    return 0


def _nodes(args: argparse.Namespace) -> int:
    registry = _make_registry(args)
    node_classes = sorted(registry.node_classes(), key=lambda node_class: node_class.type_name)

    if args.json:
        print(json.dumps([{"type": node_class.type_name,
                           "version": node_class.version,
                           "category": node_class.category,
                           "description": node_class.description,
                           "plugs": [spec.to_dict() for spec in node_class.plug_specs]}
                          for node_class in node_classes], indent=2))

        return 0

    width = max((len(node_class.type_name) for node_class in node_classes), default=0)

    for node_class in node_classes:
        print(f"{node_class.type_name:<{width}}  {node_class.category:<10}  {node_class.description}".rstrip())

    return 0


def _describe(graph: Graph, indent: str = "") -> None:
    for node in graph:
        state = " (disabled)" if node.disabled else ""

        print(f"{indent}{node.name} [{node.type_name or 'missing'}]{state}")

        for plug in node.plugs():
            sources = ", ".join(connection.source.path for connection in plug.connections if connection.target is plug)
            detail = f"<- {sources}" if sources else ("" if plug.kind is PlugKind.output else repr(plug.raw))
            print(f"{indent}    {plug.kind.value:<9} {plug.name}: {plug.spec.type_name} {detail}".rstrip())

        for child in node.child_graphs():
            _describe(child, indent + "    ")


def _info(args: argparse.Namespace) -> int:
    graph = load_graph(args.graph, _make_registry(args))

    if graph.variables:
        print("variables:")

        for name, value in graph.variables.items():
            print(f"    {name} = {value!r}")

    _describe(graph)

    return 0


def _edit(args: argparse.Namespace) -> int:
    try:
        from bolt.ui.app import Application
    except ImportError as error:
        logging.getLogger("bolt").error("the editor needs PySide6 (pip install bolt[ui]): %s", error)

        return exit_failed

    application = Application(stdlib=not args.no_stdlib, plugins=args.plugins, plugin_paths=args.plugin_paths)

    return application.run(args.files)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bolt", description="Bolt node graph engine")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="more logging, repeat for debug output")
    parser.add_argument("-q", "--quiet", action="store_true", help="only log errors")
    parser.add_argument("-p", "--plugins", dest="plugin_paths", action="append", default=[], metavar="PATH",
                        help="plugin file or directory to load (repeatable, also read from BOLT_PLUGIN_PATH)")
    parser.add_argument("--plugin", dest="plugins", action="append", default=[], metavar="MODULE_OR_PATH",
                        help="load one plugin: an importable module, a .py file or a package directory (repeatable)")
    parser.add_argument("--no-stdlib", action="store_true", help="do not load the standard node library")

    commands = parser.add_subparsers(dest="command", required=True)

    cook = commands.add_parser("cook", help="evaluate a graph file")
    cook.add_argument("graph", help="graph file to evaluate")
    cook.add_argument("-t", "--target", dest="targets", action="append", default=[], metavar="NODE",
                      help="only evaluate this node and what it depends on (repeatable)")
    cook.add_argument("-s", "--set", dest="variables", action="append", default=[], type=_parse_variable,
                      metavar="NAME=VALUE", help="set an evaluation variable, VALUE is parsed as JSON when possible")
    cook.add_argument("-o", "--output", dest="outputs", action="append", default=[], metavar="NODE.PLUG",
                      help="print the value of an output after cooking (repeatable)")
    cook.add_argument("-j", "--jobs", type=int, default=1, help="number of nodes cooked in parallel")
    cook.add_argument("-f", "--force", action="store_true", help="cook every node even if it is up to date")
    cook.add_argument("--events", action="store_true",
                      help="write the evaluation events to stdout as JSON lines instead of logging them")
    cook.add_argument("--control", action="store_true",
                      help="read pause, resume and cancel commands from stdin, one per line")
    cook.set_defaults(handler=_cook)

    nodes = commands.add_parser("nodes", help="list the available node types")
    nodes.add_argument("--json", action="store_true", help="print the node types and their plugs as JSON")
    nodes.set_defaults(handler=_nodes)

    edit = commands.add_parser("edit", help="open graph files in the editor (needs PySide6)")
    edit.add_argument("files", nargs="*", help="graph files to open")
    edit.set_defaults(handler=_edit)

    info = commands.add_parser("info", help="describe the content of a graph file")
    info.add_argument("graph", help="graph file to describe")
    info.set_defaults(handler=_info)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    level = logging.ERROR if args.quiet else (logging.DEBUG if args.verbose > 1 else logging.INFO)

    logging.basicConfig(level=level,
                        format="[%(levelname)s] %(asctime)s %(message)s",
                        datefmt="%H:%M:%S",
                        stream=sys.stderr)

    if getattr(args, "events", False):
        for name in ("bolt", "bolt.node", "bolt.evaluation"):
            logging.getLogger(name).setLevel(logging.CRITICAL if name != "bolt" else logging.WARNING)

    try:
        return args.handler(args)
    except (BoltError, OSError) as error:
        logging.getLogger("bolt").error("%s", error)

        return exit_failed


if __name__ == "__main__":
    sys.exit(main())
