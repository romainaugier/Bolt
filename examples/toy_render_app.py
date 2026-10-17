"""A host application built on the Bolt editor: the toy renderer plugin, its render view and a layout around it.

    python examples/toy_render_app.py [graph.bolt]
"""

from __future__ import annotations

import os
import sys

from bolt.ui import Application

here = os.path.dirname(os.path.abspath(__file__))

layout = {
    "type": "split", "orientation": "horizontal", "sizes": [760, 640], "children": [
        {"type": "split", "orientation": "vertical", "sizes": [560, 240], "children": [
            {"type": "pane", "views": [{"view": "node_editor"}]},
            {"type": "pane", "views": [{"view": "log"}, {"view": "node_library"}]},
        ]},
        {"type": "split", "orientation": "vertical", "sizes": [520, 280], "children": [
            {"type": "pane", "views": [{"view": "toy.render_view"}]},
            {"type": "pane", "views": [{"view": "parameters"}, {"view": "variables"}]},
        ]},
    ]}


def make_application() -> Application:
    return Application(name="Toy render", plugins=[os.path.join(here, "plugins", "toy_render")], layout=layout,
                       restore_layout=False)


if __name__ == "__main__":
    files = sys.argv[1:] or [os.path.join(here, "graphs", "toy_scene.bolt")]
    sys.exit(make_application().run(files))
