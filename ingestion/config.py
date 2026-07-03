"""Ingestion constants. Field codes are selected from the official dictionaries in
docs/ (fdic_*_properties.yaml) and were each confirmed against a live API response
on 2026-07-03 — do not add codes here without repeating both checks."""

BASE_URL = "https://api.fdic.gov/banks"  # old banks.data.fdic.gov/api host 301s here

# Scope: institutions reporting > $1B total assets in ANY quarter since 2019-Q1.
# FDIC dollar fields are reported in THOUSANDS, so $1B == 1_000_000.
MIN_ASSET_THOUSANDS = 1_000_000
FIRST_QUARTER_END = "2019-03-31"

# /financials — one row per bank-quarter. Dollar levels in thousands; *R/*Y fields
# are ratios in percent. Dictionary: docs/fdic_risview_properties.yaml
FINANCIAL_FIELDS = [
    "CERT",       # FDIC certificate number (bank id)
    "REPDTE",     # report date, YYYYMMDD
    "ASSET",      # total assets
    "DEP",        # total deposits
    "EQ",         # equity capital
    "EQR",        # equity capital ratio
    "NETINC",     # net income (year-to-date)
    "ROA",        # return on assets
    "ROE",        # return on equity
    "NIMY",       # net interest margin
    "EEFFR",      # efficiency ratio
    "LNLSNET",    # net loans and leases
    "SC",         # securities
    "NPERFV",     # nonperforming assets / total assets
    "NCLNLS",     # noncurrent loans and leases
    "NCLNLSR",    # noncurrent / gross loans ratio
    "BRO",        # brokered deposits
    "DEPUNA",     # est. uninsured deposits (domestic offices)
    "DEPUNINS",   # est. uninsured deposits (domestic + insured branches)
    "NONII",      # total noninterest income
    "NONIIR",     # noninterest income ratio
    "NTLNLS",     # net charge-offs (year-to-date)
    "NTLNLSCOR",  # net charge-offs ratio
    "INTEXPY",    # interest expense / earning assets (cost of funds)
    "RBCT1CER",   # common equity tier 1 ratio
    "RBCRWAJ",    # total risk-based capital ratio
    "RBC1AAJ",    # leverage ratio
]

# /institutions — one row per institution. Dictionary: docs/fdic_institution_properties.yaml
# ASSET and DEP are not in the API's default field set — they must be requested.
INSTITUTION_FIELDS = [
    "CERT", "NAME", "CITY", "STALP", "STNAME", "ZIP", "ACTIVE", "BKCLASS",
    "ESTYMD", "ENDEFYMD", "CHANGEC1", "FED_RSSD", "WEBADDR", "DATEUPDT",
    "ASSET", "DEP",
]

# /failures — one row per failure event. Dictionary: docs/fdic_failure_properties.yaml
# ID is the API's own row identifier (returned on every record): 1930s-era records
# have NULL CERT, so (CERT, FAILDATE) is NOT unique — ID is the only safe key.
FAILURE_FIELDS = [
    "ID", "CERT", "NAME", "FAILDATE", "FAILYR", "RESTYPE", "RESTYPE1", "CITYST",
    "QBFASSET", "QBFDEP", "SAVR", "CHCLASS1",
]
