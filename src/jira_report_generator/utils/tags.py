class Tag:
    attrs: dict = {}
    value: str
    tag: str

    def __init__(self, value="", **attrs):
        self.value = value
        self.attrs = attrs

    def __str__(self):
        result = []
        attrs = " ".join([
            f"{key}=\"{value}\""
            for key, value
            in self.attrs.items()
        ])

        result.append(f"<{self.tag} {attrs}>")
        result.append(str(self.value))
        result.append(f"</{self.tag}>")

        return "".join(result)


class TD(Tag):
    tag = "td"


class TH(Tag):
    tag = "th"


class A(Tag):
    tag = "a"


class TR(Tag):
    tag = "tr"
    columns = None
    value = None

    def __init__(self, columns: list = None, **attrs):
        self.columns = columns or []
        self.attrs = attrs

    def __str__(self):
        self.value = "".join(map(str, self.columns))
        return super().__str__()

    def append(self, column: TD):
        self.columns.append(column)


class Table(Tag):
    tag = "table"
    rows = None
    value = None

    def __init__(self, rows: list = None, **attrs):
        self.rows = rows or []
        self.attrs = attrs

    def __str__(self):
        self.value = "".join(map(str, self.rows))
        return super().__str__()

    def append(self, row: TR):
        self.rows.append(row)
