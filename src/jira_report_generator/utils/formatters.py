def format_name(name: str) -> str:
    """Format name

    Turns "User Local Host" into "User L. H.".

    """
    name_list = name.split()

    return " ".join([
        name_list[0] if name_list else "",
        *[f"{s[0]}." for s in name_list[1:] if s],
    ])
