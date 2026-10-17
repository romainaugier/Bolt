from bolt.ui.views.base import View, ViewRegistry
from bolt.ui.views.jobs import JobsView
from bolt.ui.views.library import NodeLibraryView
from bolt.ui.views.log import LogView
from bolt.ui.views.node_editor import NodeEditorView
from bolt.ui.views.parameters import ParametersView
from bolt.ui.views.theme_editor import ThemeEditorView
from bolt.ui.views.variables import VariablesView

builtin_views = (NodeEditorView, ParametersView, NodeLibraryView, LogView, VariablesView, JobsView, ThemeEditorView)

__all__ = ["JobsView", "LogView", "NodeEditorView", "NodeLibraryView", "ParametersView", "ThemeEditorView",
           "VariablesView", "View", "ViewRegistry", "builtin_views"]
