import re
from dataclasses import dataclass

import bs4

from sec_parser.utils.bs4_.get_single_table import get_single_table


@dataclass
class ApproxTableMetrics:
    rows: int
    numbers: int


def get_approx_table_metrics(bs4_tag: bs4.Tag) -> ApproxTableMetrics:
    table = get_single_table(bs4_tag)
    rows = sum(1 for row in table.find_all("tr") if row.find("td").text.strip())
    numbers = sum(
        bool(re.search(r"\d", cell.text))
        for cell in table.find_all("td")
        if cell.text.strip()
    )
    return ApproxTableMetrics(rows, numbers)
