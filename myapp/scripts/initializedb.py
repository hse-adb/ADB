import csv
from pathlib import Path

from clld.cliutil import Data
from clld.db.models import common

import myapp
from myapp import models


def _csv_rows(path):
    with path.open(encoding="utf8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue
            yield {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def main(args):
    data = Data()

    data.add(
        common.Dataset,
        myapp.__name__,
        id=myapp.__name__,
        domain="localhost",
        publisher_name="",
        publisher_place="",
        publisher_url="",
        license="http://creativecommons.org/licenses/by/4.0/",
    )

    contrib = data.add(
        common.Contribution,
        "c1",
        id="c1",
        name="ADB",
    )

    data_dir = Path(__file__).parent.parent / "data"

    def _as_float(x):
        x = (x or "").strip()
        return float(x) if x else None

    for row in _csv_rows(data_dir / "languages.csv"):
        data.add(
            models.Variety,
            row["ID"],
            id=row["ID"],
            name=row["Name"],
            latitude=_as_float(row.get("Latitude")),
            longitude=_as_float(row.get("Longitude")),
        )

    for row in _csv_rows(data_dir / "parameters.csv"):
        data.add(
            models.Feature,
            row["ID"],
            id=row["ID"],
            name=row["Name"],
        )

    for row in _csv_rows(data_dir / "values.csv"):
        lid = row["Language_ID"]
        pid = row["Parameter_ID"]

        matrix = {}
        for k, v in row.items():
            if k in {"ID", "Language_ID", "Parameter_ID"}:
                continue
            matrix[k] = 1 if str(v).strip() == "1" else 0

        vs = data.add(
            common.ValueSet,
            f"{lid}-{pid}",
            id=f"{lid}-{pid}",
            language=data["Variety"][lid],
            parameter=data["Feature"][pid],
            contribution=contrib,
            jsondata=matrix,
        )

        data.add(
            common.Value,
            row["ID"],
            id=row["ID"],
            name="",
            valueset=vs,
        )


def prime_cache(args):
    pass
