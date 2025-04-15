import re
import os
import math
import traceback

import bolt.utils.log as log
import bolt.utils.environment as env

from bolt.utils.singleton import Singleton

_exprPattern = re.compile(r"`[^`]*`")

_allowedExprFunctions = dict()

_allowedExprFunctions.update({ k : v for k, v in math.__dict__.items() if not k.startswith("__") })
_allowedExprFunctions.update({ k : v for k, v in str.__dict__.items() if not k.startswith("__") })
_allowedExprFunctions.update({ k : v for k, v in list.__dict__.items() if not k.startswith("__") })
_allowedExprFunctions.update({ k : v for k, v in dict.__dict__.items() if not k.startswith("__") })
_allowedExprFunctions.update({ k : v for k, v in tuple.__dict__.items() if not k.startswith("__") })
_allowedExprFunctions.update({ k : v for k, v in set.__dict__.items() if not k.startswith("__") })
_allowedExprFunctions.update({ k : v for k, v in int.__dict__.items() if not k.startswith("__") })
_allowedExprFunctions.update({ k : v for k, v in float.__dict__.items() if not k.startswith("__") })

_allowedBuiltins = ["int", "float", "str", "list", "dict", "tuple", "set", "len", "max", "min", "set", "__import__"]
_allowedBuiltinsFunctions = dict()

for allowedBuiltin in _allowedBuiltins:
    _allowedBuiltinsFunctions[allowedBuiltin] = __builtins__[allowedBuiltin]

class ExpressionEvaluator():

    """
    The expression evaluator can expand any string that contains a variable or an expression.
    Variables should be $(any_CASE) and expressions should be python code `math.sin(10)`
    """
    
    def __init__(self) -> None:
        pass

    def _var_evaluator(self, text: str) -> str:
        """ 
        Returns the text expanded with the corresponding variables values if any is present in the text
        """
        text = env.Environment().expand_string(text)

        return text

    def _expr_evaluator(self, text: str) -> str:
        """ 
        Return the text expanded with the corresponding expressions results. If any error, sets None to replace the expression
        """
        if re.search(_exprPattern, text) is not None:
            for match in re.finditer(_exprPattern, text):
                expr = match.group().replace('`', '')

                try:
                    code = compile(expr, "<string>", "eval")
                    result = eval(code, { "__builtins__" : _allowedBuiltinsFunctions }, _allowedExprFunctions)
                except Exception:
                    log.error(f"Error during expression expansion. Expression `{expr}` evaluation resulted in the following error")
                    log.error(traceback.format_exc())
                    result = "None"

                text = text.replace(match.group(), result)
                
        return text

    def expand_string(self, string: str) -> str:
        """
        Returns a string with its expressions and variables expanded
        """
        return self._expr_evaluator(self._var_evaluator(string))

    def string_contains_expr(self, text: str) -> bool:
        return _exprPattern.search(text) is not None
    
    def string_contains_var(self, text: str) -> bool:
        return env.Environment().search_in_string(text) is not None
        
class _GlobalExprEvaluator(Singleton, ExpressionEvaluator):
    
    def __init__(self) -> None:
        super().__init__(os.environ)

globalExprEvaluator = _GlobalExprEvaluator()