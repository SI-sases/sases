def run(params):
    n = params.get("number", 0)
    try:
        n = int(n)
    except (TypeError, ValueError):
        return {"success": False, "error": "number must be an integer"}
    if n < 2:
        return {"success": True, "number": n, "is_prime": False}
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return {"success": True, "number": n, "is_prime": False}
    return {"success": True, "number": n, "is_prime": True}