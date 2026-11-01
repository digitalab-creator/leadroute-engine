"""Company size and industry are shared. A person, a deal, and an owner are not."""

from dataclasses import replace

from app.constants import AccountKind
from app.ingest.records import CrmRow


def _one(values: list[object]) -> object | None:
    present = [value for value in values if value is not None and value != ""]
    if len(set(present)) == 1:
        return present[0]
    return None


def _one_kind(values: list[str]) -> str:
    present = [value for value in values if value and value != AccountKind.UNKNOWN.value]
    if len(set(present)) == 1:
        return present[0]
    return AccountKind.UNKNOWN.value


def agree_columns(
    industries: list[str | None],
    employees: list[int | None],
    countries: list[str | None],
    kinds: list[str],
) -> tuple[str | None, int | None, str | None, str]:
    industry = _one(list(industries))
    employee = _one(list(employees))
    country = _one(list(countries))
    return (
        None if industry is None else str(industry),
        None if employee is None else int(str(employee)),
        None if country is None else str(country),
        _one_kind(kinds),
    )


def fill_company_gaps(rows: list[CrmRow]) -> list[CrmRow]:
    grouped: dict[str, list[CrmRow]] = {}
    for row in rows:
        if row.company_domain:
            grouped.setdefault(row.company_domain, []).append(row)
    agreed: dict[str, tuple[str | None, int | None, str | None, str]] = {}
    for domain, members in grouped.items():
        agreed[domain] = agree_columns(
            [member.industry for member in members],
            [member.employees for member in members],
            [member.country for member in members],
            [member.account_kind for member in members],
        )
    filled: list[CrmRow] = []
    for row in rows:
        extra = agreed.get(row.company_domain or "")
        if extra is None:
            filled.append(row)
            continue
        industry, employees, country, kind = extra
        filled.append(
            replace(
                row,
                industry=row.industry or industry,
                employees=row.employees if row.employees is not None else employees,
                country=row.country or country,
                account_kind=row.account_kind
                if row.account_kind != AccountKind.UNKNOWN.value
                else kind,
            )
        )
    return filled
