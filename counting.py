def side_of_line(a, b, p):
    """Which side of the line from a to b point p is on. Only the sign matters."""
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
