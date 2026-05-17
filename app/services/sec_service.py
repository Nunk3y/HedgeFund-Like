from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests

SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"

SEC_TAXONOMIES = ("us-gaap", "ifrs-full", "dei")

FIELD_CONCEPTS: Dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "Revenue",
        "RevenueFromContractsWithCustomers",
    ],
    "gross_profit": ["GrossProfit"],
    "cost_of_revenue": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfSalesRevenue",
        "CostOfSales",
    ],
    "operating_income": ["OperatingIncomeLoss", "ProfitLossFromOperatingActivities"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "eps_basic": ["EarningsPerShareBasic", "BasicEarningsLossPerShare", "BasicEarningsLossPerShareFromContinuingOperations"],
    "eps_diluted": ["EarningsPerShareDiluted", "DilutedEarningsLossPerShare", "DilutedEarningsLossPerShareFromContinuingOperations"],
    "research_and_development": ["ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseByFunction"],
    "selling_general_admin": [
        "SellingGeneralAndAdministrativeExpense",
        "GeneralAndAdministrativeExpense",
        "SellingAndMarketingExpense",
        "AdministrativeExpense",
    ],
    "share_based_compensation": [
        "ShareBasedCompensation",
        "ShareBasedCompensationArrangementByShareBasedPaymentAwardExpense",
        "SharebasedPaymentExpense",
    ],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        "CashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByOperatingActivities",
        "CashFlowsFromUsedInOperatingActivities",
    ],
    "capital_expenditures": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsToAcquirePropertyPlantAndEquipmentAndIntangibleAssets",
        "CapitalExpendituresIncurredButNotYetPaid",
        "PaymentsForProceedsFromProductiveAssets",
        "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
        "PurchaseOfPropertyPlantAndEquipment",
    ],
    "depreciation_amortization": [
        "DepreciationDepletionAndAmortization",
        "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
        "DepreciationAndAmortization",
        "DepreciationAndAmortisationExpense",
        "DepreciationAmortisationAndImpairmentExpense",
    ],
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "CashAndCashEquivalents",
    ],
    "current_assets": ["AssetsCurrent", "CurrentAssets"],
    "current_liabilities": ["LiabilitiesCurrent", "CurrentLiabilities"],
    "total_assets": ["Assets"],
    "total_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "Equity",
        "EquityAttributableToOwnersOfParent",
    ],
    "debt_current": ["DebtCurrent", "LongTermDebtCurrent", "ShortTermBorrowings", "CurrentBorrowings", "CurrentLeaseLiabilities"],
    "debt_noncurrent": ["LongTermDebtNoncurrent", "NoncurrentBorrowings", "NoncurrentLeaseLiabilities"],
    "shares_basic": [
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "WeightedAverageNumberOfShareOutstandingBasic",
        "WeightedAverageNumberOfOrdinarySharesOutstandingBasic",
    ],
    "shares_diluted": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingDiluted",
        "WeightedAverageNumberOfOrdinarySharesOutstandingDiluted",
        "EntityCommonStockSharesOutstanding",
    ],
}

FALLBACK_CONCEPT_RULES = {
    "operating_cash_flow": [
        ["cash", "operating", "activities"],
        ["cash", "operations"],
    ],
    "capital_expenditures": [
        ["payments", "acquire", "property", "plant", "equipment"],
        ["payments", "acquire", "productive", "assets"],
        ["payments", "purchase", "property", "equipment"],
        ["purchase", "property", "plant", "equipment"],
        ["capital", "expenditure"],
    ],
}

INSTANT_FIELDS = {"cash_and_equivalents", "current_assets", "current_liabilities", "total_assets", "total_equity", "debt_current", "debt_noncurrent"}
INCOME_CASH_FLOW_HISTORY_FIELDS = [
    "revenue", "gross_profit", "cost_of_revenue", "operating_income", "net_income",
    "eps_basic", "eps_diluted", "research_and_development", "selling_general_admin",
    "share_based_compensation", "operating_cash_flow", "capital_expenditures",
    "depreciation_amortization", "shares_basic", "shares_diluted",
]
BALANCE_SHEET_HISTORY_FIELDS = [
    "cash_and_equivalents", "current_assets", "current_liabilities",
    "total_equity", "debt_current", "debt_noncurrent",
]
HISTORICAL_FIELDS = INCOME_CASH_FLOW_HISTORY_FIELDS + BALANCE_SHEET_HISTORY_FIELDS


@dataclass(frozen=True)
class SecFact:
    field: str
    concept: str
    unit: str
    value: Any
    fy: Optional[int]
    fp: Optional[str]
    form: Optional[str]
    filed: Optional[str]
    start: Optional[str]
    end: Optional[str]
    accn: Optional[str]
    frame: Optional[str]


def cik10(cik: int) -> str:
    return str(cik).zfill(10)


def sec_get_json(url: str, user_agent: str, delay: float = 0.25) -> Any:
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate", "Accept": "application/json"}
    time.sleep(delay)
    response = requests.get(url, headers=headers, timeout=45)
    if response.status_code != 200:
        raise RuntimeError(f"SEC HTTP {response.status_code}: {response.text[:500]}")
    return response.json()


def load_ticker_map(user_agent: str) -> Dict[str, int]:
    data = sec_get_json(SEC_TICKER_URL, user_agent)
    out = {}
    for row in data.values():
        ticker = str(row.get("ticker", "")).upper().strip()
        cik = row.get("cik_str")
        if ticker and cik is not None:
            out[ticker] = int(cik)
    return out


def companyfacts_for_cik(cik: int, user_agent: str) -> dict:
    return sec_get_json(SEC_COMPANYFACTS_URL.format(cik10=cik10(cik)), user_agent)


def concept_units(companyfacts: dict, concept: str) -> dict:
    facts = companyfacts.get("facts", {})
    for taxonomy in SEC_TAXONOMIES:
        units = facts.get(taxonomy, {}).get(concept, {}).get("units", {})
        if units:
            return units
    return {}


def all_sec_concepts(companyfacts: dict) -> list[str]:
    concepts = []
    facts = companyfacts.get("facts", {})
    for taxonomy in SEC_TAXONOMIES:
        for concept in facts.get(taxonomy, {}).keys():
            if concept not in concepts:
                concepts.append(concept)
    return concepts


def fallback_concepts_for_field(companyfacts: dict, field: str) -> list[str]:
    rules = FALLBACK_CONCEPT_RULES.get(field, [])
    if not rules:
        return []

    matches = []
    for concept in all_sec_concepts(companyfacts):
        low = concept.lower()
        for rule in rules:
            if all(token in low for token in rule):
                matches.append(concept)
                break
    return sorted(matches)


def concepts_for_field(companyfacts: dict, field: str) -> list[str]:
    out = []
    for concept in FIELD_CONCEPTS[field] + fallback_concepts_for_field(companyfacts, field):
        if concept not in out:
            out.append(concept)
    return out


def choose_best_unit(units: dict) -> Optional[str]:
    for unit in ("USD", "TWD", "shares", "USD/shares", "TWD/shares", "pure"):
        if unit in units:
            return unit
    return next(iter(units.keys()), None)


def is_annual_fact(fact: dict) -> bool:
    form = str(fact.get("form") or "")
    fp = str(fact.get("fp") or "")
    frame = str(fact.get("frame") or "")
    return form in {"10-K", "20-F", "40-F"} or fp == "FY" or (frame.startswith("CY") and not frame.endswith("Q"))


def is_quarterly_or_annual_fact(fact: dict) -> bool:
    return str(fact.get("form") or "") in {"10-K", "10-Q", "20-F", "40-F", "6-K"}


def fact_sort_key(fact: dict) -> Tuple[int, str, str, int]:
    form = str(fact.get("form") or "")
    form_bonus = 2 if form in {"10-K", "20-F", "40-F"} else 1 if form in {"10-Q", "6-K"} else 0
    filed = str(fact.get("filed") or "")
    end = str(fact.get("end") or "")
    try:
        fy = int(fact.get("fy") or 0)
    except Exception:
        fy = 0
    return form_bonus, filed, end, fy


def fact_fiscal_year(fact: dict) -> int:
    try:
        fy = int(fact.get("fy") or 0)
    except Exception:
        fy = 0
    if fy <= 0:
        end = str(fact.get("end") or "")
        if len(end) >= 4 and end[:4].isdigit():
            fy = int(end[:4])
    if fy <= 0:
        filed = str(fact.get("filed") or "")
        if len(filed) >= 4 and filed[:4].isdigit():
            fy = int(filed[:4])
    return fy


def make_fact(field: str, concept: str, unit: str, raw: dict) -> SecFact:
    return SecFact(field, concept, unit, raw.get("val"), raw.get("fy"), raw.get("fp"), raw.get("form"), raw.get("filed"), raw.get("start"), raw.get("end"), raw.get("accn"), raw.get("frame"))


def latest_fact_for_field(companyfacts: dict, field: str) -> Optional[SecFact]:
    annual_only = field not in INSTANT_FIELDS
    for concept in concepts_for_field(companyfacts, field):
        units = concept_units(companyfacts, concept)
        if not units:
            continue
        unit = choose_best_unit(units)
        if not unit:
            continue
        candidates = []
        for raw in units.get(unit, []):
            if "val" not in raw:
                continue
            if annual_only and not is_annual_fact(raw):
                continue
            if not annual_only and not is_quarterly_or_annual_fact(raw):
                continue
            candidates.append(raw)
        if candidates:
            candidates.sort(key=fact_sort_key, reverse=True)
            return make_fact(field, concept, unit, candidates[0])
    return None


def annual_history_for_field(companyfacts: dict, field: str, max_years: int = 5) -> list[SecFact]:
    by_year = {}
    for concept in concepts_for_field(companyfacts, field):
        units = concept_units(companyfacts, concept)
        if not units:
            continue
        unit = choose_best_unit(units)
        if not unit:
            continue
        for raw in units.get(unit, []):
            if "val" not in raw:
                continue
            if not is_annual_fact(raw) and concept != "EntityCommonStockSharesOutstanding":
                continue
            fy = fact_fiscal_year(raw)
            if fy <= 0:
                continue
            normalized_raw = dict(raw)
            normalized_raw["fy"] = fy
            fact = make_fact(field, concept, unit, normalized_raw)
            existing = by_year.get(fy)
            if existing is None:
                by_year[fy] = fact
            else:
                existing_raw = {"form": existing.form, "filed": existing.filed, "end": existing.end, "fy": existing.fy}
                if fact_sort_key(normalized_raw) > fact_sort_key(existing_raw):
                    by_year[fy] = fact
    return [by_year[y] for y in sorted(by_year.keys(), reverse=True)[:max_years]]


def row(ticker: str, cik: int, endpoint: str, field: str, fact: Optional[SecFact], note: str = "") -> dict:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return {
        "Ticker": ticker,
        "Timestamp": now,
        "Source": "SEC EDGAR",
        "Endpoint / Metric": endpoint,
        "Raw Field": field,
        "Raw Value": "" if fact is None else fact.value,
        "Period": "" if fact is None else (fact.fp or ""),
        "Fiscal Year": "" if fact is None else (fact.fy or ""),
        "Status": "MISSING" if fact is None else "OK",
        "Error Message": "",
        "Notes": note if note else ("" if fact is not None else "No matching SEC concept found"),
        "CIK": cik,
        "SEC Concept": "" if fact is None else fact.concept,
        "Unit": "" if fact is None else fact.unit,
        "Form": "" if fact is None else (fact.form or ""),
        "Filed": "" if fact is None else (fact.filed or ""),
        "Period Start": "" if fact is None else (fact.start or ""),
        "Period End": "" if fact is None else (fact.end or ""),
        "Frame": "" if fact is None else (fact.frame or ""),
        "Accession": "" if fact is None else (fact.accn or ""),
    }


def refresh_sec_rows(ticker: str, user_agent: str, years: int = 5) -> list[dict]:
    ticker = ticker.upper().strip()
    ticker_map = load_ticker_map(user_agent)
    cik = ticker_map.get(ticker)
    if cik is None:
        raise RuntimeError(f"Ticker not found in SEC company_tickers.json: {ticker}")

    companyfacts = companyfacts_for_cik(cik, user_agent)
    rows = []

    for field in FIELD_CONCEPTS:
        rows.append(row(ticker, cik, "companyfacts_latest", field, latest_fact_for_field(companyfacts, field)))

    for field in HISTORICAL_FIELDS:
        hist = annual_history_for_field(companyfacts, field, years)
        if not hist:
            rows.append(row(ticker, cik, "companyfacts_annual_history", f"{field}_history", None))
        else:
            for fact in hist:
                rows.append(row(ticker, cik, "companyfacts_annual_history", f"{field}_history", fact))

    shares_hist = annual_history_for_field(companyfacts, "shares_diluted", years)
    if len(shares_hist) < 4:
        basic_hist = annual_history_for_field(companyfacts, "shares_basic", years)
        by_year = {int(f.fy): f for f in shares_hist if f.fy is not None}
        for fact in basic_hist:
            if fact.fy is not None:
                by_year.setdefault(int(fact.fy), fact)
        shares_hist = [by_year[y] for y in sorted(by_year.keys(), reverse=True)[:years]]

    if shares_hist:
        latest = shares_hist[0]
        rows.append(row(ticker, cik, "derived", "shares_latest_for_dilution", latest, "Latest annual shares for dilution calculations. Uses weighted-average shares first, with DEI period-end shares as a fallback."))
        if len(shares_hist) >= 2 and shares_hist[1].value:
            val = float(latest.value) / float(shares_hist[1].value) - 1
            fact = SecFact("dilution_1y", "derived", "pure", val, latest.fy, latest.fp, latest.form, latest.filed, latest.start, latest.end, latest.accn, latest.frame)
            rows.append(row(ticker, cik, "derived", "dilution_1y", fact, "Latest annual shares / prior-year annual shares - 1."))
        else:
            rows.append(row(ticker, cik, "derived", "dilution_1y", None, "Not enough annual share history."))

        if len(shares_hist) >= 4 and shares_hist[3].value:
            val = float(latest.value) / float(shares_hist[3].value) - 1
            fact = SecFact("dilution_3y", "derived", "pure", val, latest.fy, latest.fp, latest.form, latest.filed, latest.start, latest.end, latest.accn, latest.frame)
            rows.append(row(ticker, cik, "derived", "dilution_3y", fact, "Latest annual shares / shares three fiscal years ago - 1."))
        else:
            rows.append(row(ticker, cik, "derived", "dilution_3y", None, "Not enough annual share history."))
    return rows
