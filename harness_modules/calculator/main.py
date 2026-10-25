import ast

def run(params):
    expression = params.get("expression", "")
    if not expression:
        raise ValueError("缺少 expression 参数")
    allowed_nodes = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div)
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        raise ValueError("表达式语法错误")
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            raise ValueError("表达式包含不允许的操作")
    result = eval(compile(tree, "<string>", "eval"), {"__builtins__": {}})
    return {"result": result}
