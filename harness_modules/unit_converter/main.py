def run(params):
    if "celsius" in params:
        c = float(params["celsius"])
        f = c * 9 / 5 + 32
        return {"fahrenheit": f}
    elif "fahrenheit" in params:
        f = float(params["fahrenheit"])
        c = (f - 32) * 5 / 9
        return {"celsius": c}
    else:
        raise ValueError("params must contain 'celsius' or 'fahrenheit'")
