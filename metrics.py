def percent_error(measured, truth):
    """abs(measured - truth) / truth * 100. None if truth is 0 (no percent can be computed)."""
    if truth == 0:
        return None
    return abs(measured - truth) / truth * 100


def speed_errors(predicted, truth):
    """Errors of predicted speeds against true speeds (same order, same units, every truth above 0).

    Returns {"mae_kmh": mean of |error|, "bias_kmh": mean of signed error (> 0 means reads high),
    "mape_pct": mean of |error| / truth * 100}, where error = predicted - truth.
    """
    if len(predicted) != len(truth) or not truth:
        raise ValueError("predicted and truth must be non-empty and the same length")
    if any(t <= 0 for t in truth):
        raise ValueError("every truth value must be above 0")
    errors = [p - t for p, t in zip(predicted, truth)]
    n = len(errors)
    return {
        "mae_kmh": sum(abs(e) for e in errors) / n,
        "bias_kmh": sum(errors) / n,
        "mape_pct": sum(abs(e) / t * 100 for e, t in zip(errors, truth)) / n,
    }
