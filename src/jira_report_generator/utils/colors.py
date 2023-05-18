def get_danger_color_class(expr: bool, default: str = "") -> str:
    """Get color class.

    Returns a string -- name of CSS class based on
    incoming expression.

    As example, we need to change text to red color if
    spent time > estimated time:

    >>> get_danger_color_class(spent > estimated)

    """

    if expr:
        return "danger"
    return default
