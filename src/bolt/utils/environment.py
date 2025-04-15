import os
import re
import json
import typing

import bolt.utils.log as log
import bolt.utils.filesystem as filesys

from bolt.utils.singleton import Singleton
from bolt.utils.config import Config, ConfigConstants

class Environment(Singleton):
    """
    Contains all the environment variables and the utils to find and replace them
    in a string
    
    To ease environment settings, you can provide files that can be located in the $APP_NAME_LIB/env or
    HOME/Documents/App Name/env folders. 
    Those files should be named "whatever_you_want.env" and be formatted as json files like the following :
    
    [
        { 
            "VARIABLE_NAME" : "VARIABLE_VALUE",
            "mode" : "append"
        },
        {
            "VARIABLE_NAME" : "VARIABLE_VALUE",
            "mode" : "replace"
        },
        {
            "VARIABLE_NAME" : ["VARIABLE_VALUE", "ANOTHER_VARIABLE_VALUE"],
            "mode" : "append"
        }
    ]
    
    2 modes are available: append and replace, doing what they mean.
    
    Environment also supports a context stack where variables can be organized into named contexts.
    Each context is a dictionary of variables. The most recently pushed context is checked first
    when looking for variables, followed by earlier contexts, and finally the default context.
    
    The default context is always present and cannot be deleted.
    """
    
    def __init__(self):
        """
        Initialize the Environment with a default context and empty context stack
        """
        self._default_context_name = "default"
        self._context_stack = list()
        self._default_context = dict()
        self._var_regex = None

        for var, value in os.environ.items():
            self._default_context[var] = filesys.clean_path(value)

        app_name = Config().get(ConfigConstants.AppName)
        app_root = filesys.clean_path(Config().get(ConfigConstants.AppRoot))
        app_name_upper = app_name.upper()

        self._default_context[f"{app_name_upper}_ROOT"] = app_root
        self._default_context[f"{app_name_upper}_LIB"] = f"{app_root}/library"
        self._default_context[f"{app_name_upper}_ICONS"] = f"{app_root}/library/icons"
        self._default_context[f"{app_name_upper}_PREFS"] = f"{filesys.get_documents_folder()}/{app_name}"
        self._default_context[f"{app_name_upper}_PORT"] = 45678
        
        if not os.path.exists(self.get(f"{app_name_upper}_PREFS")):
            os.makedirs(self.get(f"{app_name_upper}_PREFS"))
    
    def push_context(self, name: str, variables: typing.Dict = None) -> bool:
        """
        Push a new context onto the stack with the given name and optional variables
        
        Args:
            name (str): The name of the context
            variables (dict, optional): Initial variables for the context. Defaults to {}.
            
        Returns:
            bool: True if successful, False if a context with this name already exists
        """
        if name == self._default_context_name or any(ctx[0] == name for ctx in self._context_stack):
            log.error(f"Context with name \"{name}\" already exists")
            return False
            
        new_context = dict()

        if variables:
            new_context.update(variables)
            
        self._context_stack.append((name, new_context))

        log.info(f"Pushed new context \"{name}\" to the environment stack")

        return True
    
    def pop_context(self) -> typing.Tuple[typing.Optional[str], typing.Optional[typing.Dict]]:
        """
        Pop the most recently pushed context from the stack
        
        Returns:
            tuple: (name, variables) of the popped context, or (None, None) if stack was empty
        """
        if not self._context_stack:
            log.warning("Cannot pop context: context stack is empty")
            return None, None
            
        context = self._context_stack.pop()

        log.info(f"Popped context \"{context[0]}\" from the environment stack")

        return context
    
    def get_context(self, name: str) -> typing.Optional[typing.Dict]:
        """
        Get a context by name
        
        Args:
            name (str): The name of the context to get
            
        Returns:
            dict: The context variables, or None if not found
        """
        if name == self._default_context_name:
            return self._default_context
            
        for ctx_name, ctx_vars in self._context_stack:
            if ctx_name == name:
                return ctx_vars
                
        log.warning(f"Context \"{name}\" not found")

        return None
    
    def list_contexts(self) -> typing.List[str]:
        """
        Return a list of all context names, with the most recently pushed first
        
        Returns:
            list: List of context names
        """
        stack_names = [ctx[0] for ctx in reversed(self._context_stack)]

        return stack_names + [self._default_context_name]
    
    def get_current_context(self) -> typing.Tuple[str, typing.Dict]:
        """
        Get the name and variables of the most recently pushed context
        
        Returns:
            tuple: (name, variables) of the current context, or (default_name, default_vars) if stack is empty
        """
        if len(self._context_stack) == 0:
            return self._default_context_name, self._default_context

        return self._context_stack[-1]
    
    def get(self, key: str) -> typing.Optional[str]:
        """
        Get a variable value by checking contexts in order:
        1. Most recently pushed context first
        2. Previous contexts in order of recency
        3. Default context last
        
        Args:
            key (str): The variable name to look up
            
        Returns:
            str: The variable value or empty string if not found
        """
        for _, context in reversed(self._context_stack):
            if key in context:
                return context[key]
                
        if key in self._default_context:
            return self._default_context[key]
            
        return None

    def set(self, key: str, value: str, context_name: str = None) -> bool:
        """
        Set a variable in a specific context or the current (top) context
        
        Args:
            key (str): The variable name
            value (str): The variable value
            context_name (str, optional): The context to update. Defaults to current context.
            
        Returns:
            bool: True if successful, False if context not found
        """
        if context_name is None:
            if len(self._context_stack) > 0:
                self._context_stack[-1][1][key] = value
            else:
                self._default_context[key] = value
            return True
            
        if context_name == self._default_context_name:
            self._default_context[key] = value
            return True
            
        for i, (name, context) in enumerate(self._context_stack):
            if name == context_name:
                self._context_stack[i][1][key] = value
                return True
                
        log.error(f"Cannot set variable: context \"{context_name}\" not found")

        return False
        
    def build_environment_from_files(self, context_name: str = None) -> None:
        """
        Go through all files found in /env folders and parse them to add to
        update the environment
        
        Args:
            context_name (str, optional): The context to update. Defaults to current context.
        """
        app_name = Config().get(ConfigConstants.AppName)
        app_root = self.get(f"{app_name.upper()}_ROOT")

        app_envs = self.get(f"{app_name.upper()}_ENVS")
        
        if len(app_envs) == 0:
            app_envs = f"{app_root}/env"
        else:
            app_envs += f"{os.pathsep}{app_root}/env"
        
        prefs_dir = self.get(f"{app_name.upper()}_PREFS")
        
        if os.path.exists(f"{prefs_dir}/env"):
            app_envs += f"{os.pathsep}{prefs_dir}/env"
            
        for path in app_envs.split(os.pathsep):
            eval_path = self.expand_string(path)
            
            if os.path.exists(eval_path):
                for file in os.listdir(eval_path):
                    if ".env" in file:
                        with open(f"{eval_path}/{file}") as f:
                            try:
                                data = json.load(f)
                                
                                for env in data:
                                    for key, value in env.items():
                                        if key == "mode":
                                            continue
                                        else:
                                            old_env_value = ""
                                            
                                            if env["mode"] == "append":
                                                old_env_value = self.get(key)
                                                
                                                if old_env_value == "":
                                                    if isinstance(value, list):
                                                        for i, env_val in enumerate(value):
                                                            if i == 0:
                                                                old_env_value += f"{env_val}"
                                                            else:
                                                                old_env_value += f";{env_val}"
                                                    else:
                                                        old_env_value = value
                                                else:
                                                    if isinstance(value, list):
                                                        for env_val in value:
                                                            old_env_value += f";{env_val}"
                                                    else:
                                                        old_env_value += f";{value}"
                                            else:
                                                if isinstance(value, list):
                                                    for i, env_val in enumerate(value):
                                                        if i == 0:
                                                            old_env_value = f"{env_val}"
                                                        else:
                                                            old_env_value += f";{env_val}"
                                                else:
                                                    old_env_value = value
                                                    
                                            self.set(key, old_env_value, context_name)
                                                
                            except ValueError:
                                log.error(f"Error during json decoding, file \"{eval_path}/{file}\" will be discarded")
            else:
                log.error(f"Error during environment building, directory \"{eval_path}\" does not exist")
                        
    def build_regex(self) -> re.Pattern:
        """
        Build a regex pattern for all variables across all contexts
        
        Returns:
            re.Pattern: Compiled regex pattern matching all variables
        """
        all_vars = set()
        
        all_vars.update(self._default_context.keys())
        
        for _, context in self._context_stack:
            all_vars.update(context.keys())
            
        var_regex = r""

        for i, var in enumerate(all_vars):
            if i == 0:
                var_regex += fr"\$\({var}\)"
            else:
                var_regex += fr"|\$\({var}\)"

        return re.compile(var_regex)

    def search_in_string(self, string: str) -> bool:
        """
        Check if a string contains any environment variables
        
        Args:
            string (str): The string to check
            
        Returns:
            bool: True if the string contains environment variables, False otherwise
        """
        var_pattern = self.build_regex()

        return re.search(var_pattern, string) is not None

    def expand_string(self, string: str) -> str:
        """
        Expand all environment variables in a string
        
        Args:
            string (str): The string to expand
            
        Returns:
            str: The expanded string
        """
        var_pattern = self.build_regex()

        for match in re.finditer(var_pattern, string):
            var_name = match.group().replace("$(", "").replace(")", "")
            var_value = self.get(var_name)
            string = string.replace(match.group(), var_value)

        return string


def setenv(key: str, value: str, context: str = None) -> None:
    """
    Set an environment variable in the specified context or current context
    
    Args:
        key (str): The variable name
        value (str): The variable value
        context (str, optional): The context to update. Defaults to current context.
    """
    Environment().set(key, value, context)

def getenv(key: str) -> typing.Optional[str]:
    """
    Get an environment variable
    
    Args:
        key (str): The variable name
        
    Returns:
        str: The variable value or empty string if not found
    """
    return Environment().get(key)

def push_env_context(name: str, variables: dict = None) -> bool:
    """
    Push a new context onto the stack
    
    Args:
        name (str): The name of the context
        variables (dict, optional): Initial variables for the context. Defaults to {}.
        
    Returns:
        bool: True if successful, False if a context with this name already exists
    """
    return Environment().push_context(name, variables)

def pop_env_context() -> typing.Tuple[typing.Optional[str], typing.Optional[typing.Dict]]:
    """
    Pop the most recently pushed context from the stack
    
    Returns:
        tuple: (name, variables) of the popped context, or (None, None) if stack was empty
    """
    return Environment().pop_context()

def list_env_contexts() -> typing.List[str]:
    """
    Return a list of all context names, with the most recently pushed first
    
    Returns:
        list: List of context names
    """
    return Environment().list_contexts()

def get_env_context(name: str) -> typing.Optional[typing.Dict]:
    """
    Get a context by name
    
    Args:
        name (str): The name of the context to get
        
    Returns:
        dict: The context variables, or None if not found
    """
    return Environment().get_context(name)