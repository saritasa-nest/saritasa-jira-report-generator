from .tags import A, Div, Tag


def wrap_with_tabs(
    header: list[tuple[str, int]],
    content: list[tuple[str, int]],
) -> Tag:
    tabs_header = Div(
        *[Div(A(title, **{"href": "javascript:;"}), **{
            "class": "tab-header",
            "data-tab-header-id": id,
        }) for title, id in header],
        **{"class": "tabs-header"},
    )
    tabs_content = Div(
        *[Div(element, **{
            "class": "tab-content",
            "data-tab-content-id": id,
        }) for element, id in content],
        **{"class": "tabs-content"},
    )

    return Div(
        *[tabs_header, tabs_content],
        **{"class": "tabs"},
    )
