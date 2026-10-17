from bolt.core.registry import Registry
from bolt.stdlib import files, flow, math, process, python, strings, values

modules = (values, math, strings, files, flow, process, python)


def register(registry: Registry) -> None:
    for module in modules:
        registry.register_module(module)
