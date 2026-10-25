def run(params):
    operation = params.get("operation", "")
    text = params.get("text", "")
    if operation == "reverse":
        result = text[::-1]
    elif operation == "upper":
        result = text.upper()
    elif operation == "lower":
        result = text.lower()
    elif operation == "capitalize":
        result = text.capitalize()
    else:
        raise ValueError("operation 必须是 reverse、upper、lower 或 capitalize")
    return {"result": result}
