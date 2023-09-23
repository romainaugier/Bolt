import bolt.utils.environment as environment

def EnvEvaluator(expression: str) -> any:
    """
    Evaluates the environment in the given expression, i.e if any environment variable
    is in the expression, it will be replaced
    """
    if environment.SearchInString(expression):
        return environment.ReplaceInString(expression)
    else:
        return expression

def SafeExprEvaluator(expression : str) -> any:
    """
    Evaluates an expression, only allowing math and str functions from Python
    """
    import math
    
    allowedFunctions = {}
    
    mathFunctions = { k : v for k, v in math.__dict__.items() if not k.startswith("__") }
    allowedFunctions.update(mathFunctions)
    
    strFunctions = { k : v for k, v in str.__dict__.items() if not k.startswith("__") }
    allowedFunctions.update(strFunctions)
    
    code = compile(expression, "<string>", "eval")
    
    for name in code.co_names:
        if name not in allowedFunctions:
            raise NameError(f"The use of '{name}' is not allowed")
        
    return eval(code, {"__builtins__" : {}}, allowedFunctions)