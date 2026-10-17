<p align="center">
  <img src="src/bolt/ui/resources/icons/bolt.png" alt="Bolt logo" width="120">
</p>

<h1 align="center">Bolt</h1>

<p align="center">
  <a href="https://github.com/romainaugier/Bolt/actions/workflows/ci.yml"><img src="https://github.com/romainaugier/Bolt/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

A generic node graph engine to embed in your own applications.

Bolt started as a pipeline automation tool for a VFX student movie. Version 2 keeps the idea of reusable node graphs
but turns the core into a headless library: it knows nothing about VFX, files or user interfaces. A host application
(a pipeline tool, a renderer, a compositor...) creates its own registry of data types and nodes, builds graphs and
evaluates them. Bolt takes care of plugs and connections, type checking, expressions, caching, parallel evaluation,
events, subgraphs, loops, plugins and file I/O.

- No global state: every application owns its `Registry`, every graph owns its `EventBus`.
- Demand-driven evaluation with caching: pull one output and only the stale part of its upstream cooks.
- Variables and expressions (`$(SHOT)`, `` `FRAME * 2` ``) with automatic invalidation when a variable a node read changes.
- Serial or threaded executors, pause/resume/cancel from another thread.
- Extensible data types and conversions, so plugs can carry images, meshes or handles to native objects.
- Change tracking: nodes can ask how an input changed and get a delta (added, removed, modified items) instead of
  the whole value, so an engine fed by the graph updates incrementally.
- Live cooking of displayed nodes after every edit, or on demand, with edits during a cook restarting it or waiting.
- A job system cooking graph snapshots in child processes, with progress, logs, pause, resume and cancel.
- Plugins are plain Python modules or packages, found through entry points or plugin directories.
- Versioned JSON graph files with per-node migrations; graphs using unavailable node types load and save without loss.
- A PySide6 editor (optional) with recursive split panes, undo, and views that plugins can add.
- The core has no dependencies outside the standard library. Python 3.10+.

## Installation

```sh
pip install -e .          # the engine and the `bolt` command
pip install -e ".[ui]"    # plus the editor (PySide6), started with `bolt edit` or `bolt-editor`
pip install -e ".[dev]"   # plus pytest and PySide6
```

## Quick start

```python
import bolt


class Gain(bolt.Node):
    type_name = "comp.gain"
    category = "Color"
    inputs = (bolt.Input("image", "image", required=True),)
    parameters = (bolt.Parameter("gain", "float", 1.0),)
    outputs = (bolt.Output("result", "image"),)

    def cook(self, ctx: bolt.CookContext) -> None:
        ctx.set("result", ctx.get("image") * ctx.get("gain"))


registry = bolt.Registry()
registry.load_plugin("bolt.stdlib")
registry.register_type(bolt.DataType("image", float))
registry.register_conversion("float", "image", None)
registry.register_node(Gain)

graph = bolt.Graph(registry)
graph.create_node("values.float", "plate", values={"value": 0.5})
graph.create_node("comp.gain", "flicker", values={"gain": "`1 + 0.1 * sin(FRAME)`"})
graph.connect("plate.result", "flicker.image")

for frame in range(1, 4):
    print(graph.pull("flicker.result", variables={"FRAME": frame}))

bolt.save_graph(graph, "comp.bolt")
```

The image is a plain float to keep the example short, which is why a pass-through conversion from `float` to `image`
is registered. A real image type would come with a conversion function or a dedicated node.

`examples/embed.py` shows a host application driving a graph frame by frame, `examples/plugins/shots.py` is a
plugin defining a custom data type, and `examples/toy_render_app.py` is a complete host application: a progressive
renderer plugged into the editor (see [Plugging an engine](#plugging-an-engine-the-last-node)).

## Concepts

### Registry

`Registry()` holds the data types, the conversions between them and the node types available to graphs. It starts
with the built-in types and the core nodes (`bolt.subgraph`, `bolt.for_each`, `bolt.graph_input`,
`bolt.graph_output`). Pass `core=False` for an empty registry. Several registries can live in the same process, for
example one per host application.

### Nodes and plugs

A node type is a `Node` subclass with a dotted `type_name`. It declares its plugs as class attributes and implements
`cook(ctx)`:

| Plug kind   | Declared with | Connectable | Holds                                                   |
|-------------|---------------|-------------|---------------------------------------------------------|
| input       | `Input`       | yes         | a fallback value used when nothing is connected         |
| parameter   | `Parameter`   | no          | a value or an expression, set by the user               |
| output      | `Output`      | yes         | the value written by `cook`                             |

`Input(..., multi=True)` accepts several connections and reads as a list. `Input(..., required=True)` fails the cook
when nothing is connected. Plugs can also be added to and removed from a node instance with `add_plug` and
`remove_plug` (this is how subgraph and script nodes get their plugs). Dynamic plugs are saved with the graph.

Inputs and parameters can also be swapped on one node, as in the original Bolt: `node.set_plug_kind("radius",
PlugKind.input)` gives a parameter a plug so another node can drive it, and `node.set_plug_kind("a",
PlugKind.parameter)` turns a disconnected input into a parameter edited in place (expressions included). The cook does
not change, `ctx.get()` reads both kinds. Only plugs of editable data types can become parameters (custom types are
not editable unless declared so), multi inputs stay inputs, outputs never change. `plug.kind` is the current kind,
`plug.spec.kind` the declared one, `plug.promoted` tells them apart, and the swapped kinds are saved with the graph.

Other class attributes:

| Attribute              | Purpose                                                                                       |
|------------------------|-----------------------------------------------------------------------------------------------|
| `version`, `migrate()` | upgrade data saved by an older version of the node type                                       |
| `category`, `description`, `ui` | metadata for user interfaces                                                         |
| `context_dependencies` | variables the node reads outside of expressions; it recooks when they change                  |
| `always_cook`          | cook on every evaluation, for nodes reading external state                                    |
| `passthrough`          | output to input mapping used when the node is disabled (default: first input to first output) |
| `active_connections()` | return only the connections the cook will read, so unused branches are not evaluated          |
| `user_plugs`           | let users add and remove plugs (script and subgraph nodes); `add_user_plug()` can be overridden |
| `on_attached()`, `on_detached()` | called when the node enters or leaves a graph, e.g. to start or stop a service it owns |

Inside `cook`, the `CookContext` gives access to the node:

```python
ctx.get("name")              # input value (pulled from the connection), parameter value (expressions resolved) or output
ctx.set("name", value)       # write an output; ctx.set("name", value, delta=...) when the node knows what changed
ctx.change("name")           # the value and how it changed since this node last cooked (see Change tracking)
ctx.changed()                # names of the inputs and parameters that may have changed
ctx.context                  # the object the host application attached to the graph
ctx.variable("FRAME", 1)     # read a variable and record the dependency
ctx.expand("$(ROOT)/file")   # expand a template
ctx.info("message")          # log, also published as a NodeLog event; debug/warning/error too
ctx.progress(0.5)            # NodeProgress event
ctx.checkpoint()             # honour pause and cancel during long cooks
```

Raise `CookError("message")` to fail with a clean message. Any other exception fails the node with its traceback.

Naming: classes use CamelCase; functions, methods, variables, enum members, node and plug names use snake_case.

### Data types

`DataType(name, python_type, default=..., default_factory=..., editable=..., ui=...)` describes the values a plug
carries. Subclass it to customise `coerce`, `serialize` and `deserialize`. Built-in types: `any`, `bool`, `int`,
`float`, `string`, `path`, `code` (a string that is never expanded), `list` and `dict`. They are all `editable`: users
can type their values and files can save them, so their plugs can be switched to parameters. Custom types are not
editable by default; declare `editable=True` once values can be serialized, and register a parameter widget in the
editor if a JSON line is not enough.

Connections are type checked. `any` connects to everything, and `registry.register_conversion("image", "texture",
function)` allows a typed connection by converting values as they are pulled. Built-in conversions cover
`bool -> int -> float`, numbers to `string`, and `string <-> path`.

### Variables and expressions

A string value may contain `$(NAME)` variable references and Python expressions between backticks:

```
$(PROJECT_ROOT)/$(SHOT)/render.`f'{FRAME:04d}'`.exr  # templates expand to strings
`FRAME * 2`                                        # a lone expression keeps its Python type
`$(START) + 10`                                    # variables can be used inside expressions
```

Lists and dicts expand their string items. Expressions can use the `math` functions and a small set of builtins.
They are meant for convenience, not as a sandbox, so do not evaluate graphs from untrusted sources.

Variables are looked up in order: the variables passed to `evaluate`/`pull`, the variables of the graph, those of
its parent graphs, then the process environment. Every variable a node reads is recorded, so changing `FRAME` only
recooks the nodes that depend on it.

### Evaluation and caching

```python
result = graph.evaluate()                                   # every node
result = graph.evaluate(["render", "publish"])              # these nodes and their upstream
value = graph.pull("viewer.image", variables={"FRAME": 12}) # evaluate and return one output
stale = graph.stale_nodes()                                 # what would cook, without cooking
```

A node cooks when it was never cooked, failed, was modified (values, connections, plugs, disabled state), when an
upstream node cooked after it, or when a variable it read changed. Everything else is reused. `force=True` cooks
everything.

`EvaluationResult` lists the `cooked`, `fresh`, `failed` (with messages) and `blocked` nodes, and its `status` is
`succeeded`, `failed` or `cancelled`. A failure does not stop independent branches; nodes downstream of it are blocked.

Executors decide how the plan runs: `SerialExecutor` (default) or `ThreadedExecutor(max_workers)`, which cooks
independent branches concurrently and pays off when nodes release the GIL (subprocesses, I/O, native code). Write
your own by subclassing `Executor`. A `Control` passed to `evaluate` lets another thread `pause()`, `resume()` or
`cancel()`.

The structure of a graph cannot change while it is evaluating (`GraphBusyError`). Values can, and the edited nodes
cook again on the next evaluation. Graph edits are not thread-safe: make them from a single thread.

### Change tracking and deltas

A node that maintains state elsewhere, typically the last node feeding an engine, should not resend everything on
each cook. `ctx.change(name)` returns a `Change` with the value and its `kind`:

- `unchanged`: the same value as at this node's last successful cook;
- `delta`: `change.delta` describes what changed, e.g. a `MappingDelta(added, removed, modified)` for dicts;
- `replaced`: no delta is available, use the whole value.

```python
def cook(self, ctx):
    change = ctx.change("scene")
    if change.kind is bolt.ChangeKind.delta:
        engine.update(change.delta.added, change.delta.removed, change.delta.modified)
    elif change.kind is bolt.ChangeKind.replaced:
        engine.load(change.value)
```

Deltas come in layers. A producer that knows what it changed passes it: `ctx.set("scene", scene, delta=...)`.
Otherwise the output's data type computes one with `DataType.diff(old, new)`. The built-in `dict` and `list` types
diff by identity: an item that is the same Python object is unchanged, so the cost is the number of items, not
their size. When a consumer skipped several cooks of its input, the steps are combined with `DataType.merge`. When
nothing applies, the change is `replaced`, which is always correct, only slower. Tracking starts lazily the first
time a node asks for a change on a connection, so graphs that never use deltas pay nothing. Deltas also cross
subgraph boundaries. Custom types get deltas by implementing `diff`, `merge` and, for verification, `apply`.

This relies on one rule: **never modify an input in place**. Copy what you change and share the rest
(copy-on-write): `bolt.copy_with(scene, {"moon": moved_moon})` returns a new dict sharing every other item.
`graph.evaluate(strict=True)` enforces it: it fails a node that mutated its inputs (compared with
`DataType.fingerprint`) or wrote a delta that does not turn the previous value into the new one.

### Live cooking

Nodes have a display flag (`node.displayed`, saved with the graph). A `LiveCooker` cooks the displayed nodes of a
graph on a background thread:

```python
live = bolt.LiveCooker(graph, mode=bolt.LiveMode.auto, policy=bolt.EditPolicy.restart)
live.set_variables({"FRAME": 12})   # variables for the cooks, changing them triggers a cook in auto mode
live.cook()                         # cook now; live.cook([node]) cooks given nodes once
live.edit(lambda: graph.connect("a.out", "b.in"))   # structural edits go through edit()
```

In `auto` mode every edit schedules a cook (debounced), in `manual` mode only `cook()` does; without displayed node,
a manual cook cooks the whole graph and an auto cook does nothing. When an edit arrives during a cook, the `restart`
policy cancels it and cooks again, the `finish` policy lets it end and cooks again afterwards. Structural edits cannot
happen during a cook, so `edit()` runs them immediately when idle and queues them otherwise (`call_soon` lets a UI
run the queued edits on its own thread). Value edits are always immediate.

### Host context

`Graph(registry, context=my_app)` attaches any object to a graph and its subgraphs. Nodes read it as `ctx.context`
during their cook: that is how a node reaches a service owned by the host, such as a renderer, a database or a
farm client, without global state.

### Events

Each graph publishes events on its `EventBus` (subgraphs share their parent's bus):

- edits: `NodeAdded`, `NodeRemoved`, `NodeRenamed`, `NodeChanged`, `PlugAdded`, `PlugRemoved`, `ValueChanged`,
  `Connected`, `Disconnected`, `VariableChanged`
- evaluation: `EvaluationStarted`, `EvaluationProgress`, `EvaluationFinished`, `NodeCookStarted`, `NodeCooked`,
  `NodeCookFailed`, `NodeBlocked`, `NodeLog`, `NodeProgress`

```python
subscription = graph.events.subscribe(bolt.events.NodeCooked, lambda event: print(event.node.path, event.duration))
subscription.close()
```

Subscribing to a class also receives its subclasses, so `subscribe(bolt.Event, ...)` sees everything. Applications
and plugins define their own events as frozen dataclasses deriving from `bolt.Event` and publish them with
`bus.dispatch(event)` or `bus.emit(EventType, *fields)`. `emit` builds nothing when no one listens. Evaluation events
are published from the thread that cooks the node, so a UI has to forward them to its main thread.

### Automatic layout

`bolt.core.layout.sugiyama_layout(sizes, edges, hints, options)` places boxes in layers flowing left to right and
returns their top-left corners. It knows nothing about Qt or Bolt nodes, so other front ends can reuse it: give it
`{key: (width, height)}`, `LayoutEdge(source, target, source_offset, target_offset)` with the ports' heights inside
the boxes, and optionally the current y of each box to keep the user's vertical order.

It lays out connected components separately and stacks them, reverses back edges to break cycles, assigns layers by
longest path and then moves nodes right next to their consumers, inserts dummy nodes along long edges, reduces
crossings with port-aware barycenter sweeps (keeping the best order found), and places nodes vertically so that
connected ports line up as much as possible (weighted isotonic regression under the order and spacing constraints).
`LayoutOptions` sets the gaps, the number of sweeps and an optional grid; 1500 nodes take about 0.2 s.

### Subgraphs and loops

`bolt.subgraph` nodes contain a graph with an `inputs` and an `outputs` node. `add_subgraph_input` and
`add_subgraph_output` create matching plugs on both sides. The subgraph recooks only what changed inside.

`bolt.for_each` runs its subgraph once per item of its `items` input. Inside, `inputs.item` and `inputs.index` give
the current element, and the values reaching `outputs.result` are gathered into the `results` list.

### Jobs

A `JobManager` cooks snapshots of graphs in child processes (`bolt cook --events --control`), a limited number at a
time. The child loads the same plugins as the registry the manager was given, reports its progress and logs as JSON
events, and obeys `pause`, `resume` and `cancel` sent on its standard input.

```python
jobs = bolt.JobManager(registry, max_running=2)
jobs.events.subscribe(bolt.JobChanged, lambda event: print(event.job.name, event.job.status, event.job.progress))
job = jobs.submit(graph, targets=["publish"], variables={"SHOT": "sh010"})
job.pause(); job.resume(); job.cancel()
job.wait()
```

### Files

```python
bolt.save_graph(graph, "shot.bolt")
graph = bolt.load_graph("shot.bolt", registry)
text = bolt.dumps(graph); graph = bolt.loads(text, registry)
```

Graph files are JSON: the graph variables, the nodes (type, version, values, dynamic plugs, metadata, nested graphs)
and the connections. Saving is atomic. Older node versions go through `Node.migrate`. Nodes whose type is not
registered load as `MissingNode`: they fail when cooked but keep their data and connections, so saving the graph
does not lose them. Node `metadata` is free-form, for example to store UI positions.

### Plugins

A plugin is a module, a `.py` file or a package directory. If it defines `register(registry)`, that function is
called. Otherwise every `Node` subclass with a `type_name` and every `DataType` defined at its top level is
registered.

```python
registry.load_plugin("my_studio.nodes")         # importable module
registry.load_plugin("/path/to/plugin.py")      # file or package directory
errors = registry.discover_plugins(["/studio/bolt_plugins"])
```

`discover_plugins` loads the `bolt.plugins` entry point group, then every plugin found in the directories listed in
`BOLT_PLUGIN_PATH`, then in the given directories. It returns the failures instead of raising them. A host
application can pass its own `entry_point_group` and `environment_variable`. To publish a plugin as an installable
package:

```toml
[project.entry-points."bolt.plugins"]
my_nodes = "my_studio.nodes"
```

## Editor

`bolt edit [files]` (or `bolt-editor`) opens the editor with the standard library and the discovered plugins.

- **Panes**: every pane is a tab group of views. Split it left/right or top/bottom, close it, add views with `+`.
  Layouts are recursive, saved on exit, and can be saved by name (Window menu).
- **Node editor**: `Tab` searches and creates nodes, drag from a plug to connect (compatible plugs are highlighted and
  the curve snaps to the one under the cursor), drag from a connected input to move or remove a connection, `Delete`
  removes, `Ctrl+C`/`Ctrl+V`/`Ctrl+D` copy, paste and duplicate, `F` frames, double-click or `Enter` enters a subgraph
  and `U` goes up, `R` toggles the display flag and `Q` the disable flag (both also clickable in the node header),
  middle button or `Alt` drag pans. `G` (or the grid button) shows the grid, saved with the layout; hold `Shift` while
  moving nodes to snap them to it. Plugs sit on grid lines, so connections between snapped nodes of the same row are
  straight. `L` (or the layout button, or the context menu) arranges the selected nodes in layers, or the whole graph
  when nothing is selected, on the grid and in one undo step.
- **Parameters**: editors chosen per data type or `ui` hint; the `ƒ` button switches a value to an expression; the
  plug button next to a parameter makes it an input of the node, and the parameter button next to an input makes it
  a parameter again (disconnecting it, undoably); right-clicking a plug in the node editor does the same;
  nodes with user plugs get a plug editor.
- **Cooking**: the toolbar switches between auto and manual live cooking, chooses what an edit does during a cook,
  cooks (`F5`), stops, and submits the graph as a job. Every edit can be undone.
- Other views: node library (double-click or drag), log, graph and live variables, jobs, theme.

### Themes

The editor keeps the look of the original Bolt: dark rounded nodes with a drop shadow, plugs colored by data type,
connections fading from the source plug's color to the target's, a yellow selection outline and a dark veil on
disabled nodes. Widgets are flat: borderless fields, thin chevrons on combo boxes, spin boxes and trees, no mnemonic
underlines in menus (`Alt` shortcuts still work). This comes from `bolt.ui.theme.BoltStyle`, a Fusion proxy style that
a host building its own window gets with `theme.apply(application)`. Every color and a few shapes (node corner
radius, shadow offset, connection width) belong to a theme.

**Window > Theme editor…** (or the *Theme* view in any pane) edits it live: pick a preset (*Deep ocean*, *Palenight*),
click a swatch or type a color (`#rrggbb`, or `#aarrggbb` with transparency), and import or export themes as JSON.
The theme is saved with the application settings and restored on the next start. A theme file may define only some
roles; the others come from the default preset:

```json
{"name": "Mine", "colors": {"canvas": "#202020", "type_float": "#89ddff"}, "metrics": {"node_radius": 4}}
```

Node types choose their header with `ui`: `{"style": "subgraph"}`, `"loop"` or `"branch"` use the theme's colors for
those roles (subgraph, for-each and switch nodes already do), and `{"color": "#3d6e8f"}` forces a color. Plugs of the
built-in data types use the theme's type colors; other types use their own `ui` color, or one derived from their name.

In code, `theme.<role>` (`theme.text`, `theme.node_header`...) always returns the current color, so custom views that
paint read it in `paintEvent` and follow theme changes for free. Widgets styled once connect to
`theme.notifier().changed` (icons do it with `bind_icon`, below). `theme.set_theme(theme.presets["Palenight"])`
switches from code.

### Icons

Icons come from an `IconLibrary` (`bolt.ui.icons.library`), the icon library of the original Bolt: folders of images
looked up by file name. Bolt ships a selection of Google's [Material Symbols](https://fonts.google.com/icons) (Rounded,
Apache 2.0, see `bolt/ui/resources/icons/LICENSE-material-symbols.txt`) under their Material names, plus the Bolt
logo shown in the window title and the menu bar. The icons are monochrome SVGs painted in theme colors, sharp at any
size:

```python
from bolt.ui.icons import bind_icon, library

library.icon("save", theme.text)              # QIcon rendered at 16 to 64 px
library.pixmap("tune", 18, theme.node_text)   # QPixmap fitted in 18x18, painted in a color
bind_icon(button, "vertical_split")           # icon in the theme's text color, repainted when the theme changes
bind_icon(action, "close", "muted")           # another theme role
bind_icon(action, "logo", None)               # a colored image kept as is
```

Nodes show their state in the header (`schedule`, `check_circle-fill`, `error-fill`, `warning-fill`, and a turning
progress arc while cooking, `icons.Spinner`), and document tabs show the graph's last cook. A node type shows an icon
before its title with `ui = {"icon": "deployed_code"}`, any name of the library or the path of an image file. To use
more Material Symbols, download them (the `@material-symbols/svg-400` npm package has them all) and register their
folder with `ui.register_icons(folder)`; PNG, GIF and JPEG files work too, and names override the built-in ones.

### Extending the editor

A plugin may define `register_ui(ui)` next to `register(registry)`. It is only called by the editor, so a plugin
never imports Qt when used headless (import your Qt modules inside `register_ui`).

```python
def register_ui(ui):
    from .view import RenderView, ColorEditor
    ui.register_view(RenderView)                      # a bolt.ui.View subclass, available in every pane
    ui.register_parameter_widget("color", ColorEditor)  # editor for plugs whose type or ui hint is "color"
    ui.register_icons(os.path.join(os.path.dirname(__file__), "icons"))  # names override the built-in icons
```

A view receives the `Workspace`: the registry, open documents (graph, undo stack, live cooker), the selection, the
job manager, and `workspace.events`, a bus on which every event of interest arrives on the GUI thread: graph
events of all documents, job events and the editor's own events (`SelectionChanged`, `CurrentGraphChanged`...).
`View.subscribe()` unsubscribes automatically when the view closes. When an edit made through a view's own widgets
makes the view rebuild them, defer the rebuild (`QTimer.singleShot(0, self, ...)`) and release old widgets with
`deleteLater()`: Qt crashes if a widget is destroyed while it is still emitting the signal that caused the edit.
For the same reason, Python's garbage collector must never free Qt objects on a cooking or render thread:
`Application` runs it on the GUI thread only with `bolt.ui.GarbageCollector`, which a host building its own window
should start as well. Host applications build their own editor with
`bolt.ui.Application(registry, name=..., context=..., plugins=..., views=..., layout=...)`.

### Plugging an engine: the last node

Bolt stays a general-purpose graph runner; an engine plugs in through an ordinary node that ends the graph and a
view that shows the engine's output. `examples/plugins/toy_render` is the reference:

- the scene nodes produce immutable values and share unchanged ones (copy-on-write), so the scene diffs by identity;
- `toy.render` is the last node: it owns a `RenderSession` (created in `on_attached`), reads `ctx.change("scene")`
  and sends deltas, or the whole scene when there is no delta, to the session; its cook only hands data over;
- the session renders progressively on its own thread, re-rendering only the screen region a delta touched, and
  calls its listeners after each bucket;
- the render view gives the session's pixel buffer to an `ImageCanvas` once; the listener only calls
  `canvas.request_update()`, a thread-safe, coalesced repaint that wraps the buffer without copying it.

With the render node displayed and auto cooking on, editing a sphere re-renders only that sphere's area. Run it with
`python examples/toy_render_app.py`.

## Standard library

`registry.load_plugin("bolt.stdlib")`, or individual modules such as `bolt.stdlib.math`:

| Module    | Node types                                                                                     |
|-----------|------------------------------------------------------------------------------------------------|
| values    | `values.int`, `values.float`, `values.bool`, `values.string`, `values.path`, `values.list`, `values.dict` |
| math      | `math.add`, `math.subtract`, `math.multiply`, `math.divide`, `math.sum`                        |
| strings   | `string.format`, `string.join`, `string.replace`                                               |
| files     | `files.list_directory`, `files.exists`, `files.join_path`, `files.make_directory`, `files.copy` |
| flow      | `flow.switch` (lazy), `flow.merge`, `flow.passthrough`, `flow.log`, `flow.fail`, `flow.sleep`  |
| process   | `process.run`: runs a program, streams its output to the log, can be cancelled                 |
| python    | `python.script`: Python code with user-defined inputs and outputs                              |

## Command line

```sh
bolt nodes                                              # list node types (--json for plugs too)
bolt info shot.bolt                                     # describe a graph
bolt cook shot.bolt -s FRAME=1001 -s SHOT=sh010         # evaluate with variables (values parsed as JSON)
bolt cook shot.bolt -t publish -j 8 -o publish.path     # one target, 8 threads, print an output
bolt -p ./plugins cook shot.bolt                        # load the plugins of a directory
bolt --plugin my_studio.nodes cook shot.bolt            # load one plugin (module, file or package directory)
bolt cook shot.bolt --events --control                  # JSON events on stdout, pause/resume/cancel on stdin
bolt edit shot.bolt                                     # open the editor
```

`bolt` exits with 0 on success, 1 when a node fails and 130 when interrupted with Ctrl+C, which cancels the
evaluation cleanly.

## Development

```sh
pip install -e ".[dev]"
pytest
pytest --cov --cov-report=term --cov-report=html   # coverage report in htmlcov/
```

The UI tests run without a display on the `offscreen` Qt platform (the default in `tests/ui/conftest.py`).

Continuous integration (`.github/workflows/ci.yml`) runs the tests on Linux, macOS and Windows, each on x86_64 and
arm64 (`ubuntu-24.04`, `ubuntu-24.04-arm`, `macos-15-intel`, `macos-15`, `windows-2025`, `windows-11-arm`), with
Python 3.13 and 3.14. A separate job measures coverage on Linux with Python 3.14: the report appears in the run summary
and is attached to the run as `coverage.xml` and an HTML report.

## Roadmap

- Submitting jobs to render farms, built on the same event stream as local jobs.
- Per-pane graph navigation and network boxes in the node editor.

Graph files from Bolt 1 (`.bgraph`, `.fgraph`) and `.bnode` definitions are not supported by this version.
