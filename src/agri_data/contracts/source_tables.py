"""Read provider HTML tables without executing scripts or parsing commented examples."""

from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass
class Cell:
    text: str
    rowspan: int = 1
    colspan: int = 1


@dataclass
class Table:
    attributes: dict
    rows: list = field(default_factory=list)

    def grid(self, maximum_cells=1_000_000):
        occupied = {}
        for y, row in enumerate(self.rows):
            x = 0
            for cell in row:
                while (y, x) in occupied:
                    x += 1
                if cell.rowspan * cell.colspan + len(occupied) > maximum_cells:
                    raise ValueError("Source table exceeds the declared parsing budget")
                for dy in range(cell.rowspan):
                    for dx in range(cell.colspan):
                        key = (y + dy, x + dx)
                        if key in occupied:
                            raise ValueError("Overlapping source table spans")
                        occupied[key] = cell.text
                x += cell.colspan
        if not occupied:
            return []
        height = max(y for y, _ in occupied) + 1
        width = max(x for _, x in occupied) + 1
        if height != len(self.rows) or height * width > maximum_cells:
            raise ValueError("Invalid source table dimensions")
        if len(occupied) != height * width:
            raise ValueError("Incomplete source table rows")
        return [[occupied[y, x] for x in range(width)] for y in range(height)]


class SourceHTML(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tables, self.headings, self.links = [], [], []
        self.selects, self.inputs = {}, {}
        self._tables = []
        self._heading = self._link = self._select = self._option = None
        self._skip = 0
        self.feed(text)
        self.close()
        if self._tables:
            raise ValueError("Unclosed source table")

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self._skip += 1
            return
        if self._skip:
            return
        if tag == "table":
            self._tables.append({"table": Table(attrs), "row": None, "cell": None})
        elif self._tables and tag == "tr":
            if self._tables[-1]["row"] is not None:
                raise ValueError("Unclosed source row")
            self._tables[-1]["row"] = []
        elif self._tables and tag in ("th", "td"):
            spans = [int(attrs.get(key, "1")) for key in ("rowspan", "colspan")]
            if not all(1 <= value <= 100_000 for value in spans):
                raise ValueError("Invalid source table span")
            self._tables[-1]["cell"] = ([], spans)
        elif tag in ("h1", "h2", "h3"):
            self._heading = (tag, [])
        elif tag == "a":
            self._link = (attrs.get("href", ""), [])
        elif tag == "select":
            self._select = attrs.get("name")
            if self._select:
                self.selects.setdefault(self._select, [])
        elif tag == "option" and self._select:
            self._option = (attrs.get("value", ""), [])
        elif tag == "input" and attrs.get("name"):
            self.inputs[attrs["name"]] = attrs.get("value", "")
        if tag == "br":
            self.handle_data(" ")

    def handle_data(self, data):
        if self._skip:
            return
        if self._tables and self._tables[-1]["cell"] is not None:
            self._tables[-1]["cell"][0].append(data)
        for current in (self._heading, self._link, self._option):
            if current is not None:
                current[1].append(data)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if self._tables:
            current = self._tables[-1]
            if tag in ("td", "th") and current["cell"] is not None:
                parts, spans = current["cell"]
                if current["row"] is None:
                    raise ValueError("Source cell is outside a row")
                current["row"].append(Cell(" ".join("".join(parts).split()), *spans))
                current["cell"] = None
            elif tag == "tr" and current["row"] is not None:
                current["table"].rows.append(current["row"])
                current["row"] = None
            elif tag == "table":
                if current["row"] is not None or current["cell"] is not None:
                    raise ValueError("Unclosed source row or cell")
                self.tables.append(self._tables.pop()["table"])
        if tag in ("h1", "h2", "h3") and self._heading:
            self.headings.append((self._heading[0], " ".join("".join(self._heading[1]).split())))
            self._heading = None
        elif tag == "a" and self._link:
            self.links.append((self._link[0], " ".join("".join(self._link[1]).split())))
            self._link = None
        elif tag == "option" and self._option and self._select:
            self.selects[self._select].append(
                (self._option[0], " ".join("".join(self._option[1]).split())))
            self._option = None
        elif tag == "select":
            self._select = None

    def table(self, identifier):
        found = [table for table in self.tables if table.attributes.get("id") == identifier]
        if len(found) != 1:
            raise ValueError("Expected exactly one identified source table")
        return found[0]
