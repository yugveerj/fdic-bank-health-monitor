"""Generate the Tableau Public satellite workbook (fdic_peer_satellite.twb).

Tableau Public has no publish API, so the workbook itself is the deliverable:
the owner opens this file in Tableau Desktop, signs into Google when prompted,
and clicks Save to Tableau Public. The XML here is authored against the
structure of real workbooks built in Tableau Desktop 2026.1 with the Google
Drive connector (the current way Desktop reads Google Sheets — the Sheet is
fetched as an exported xlsx via the Drive API, and the connection prompts for
OAuth on open because no credential is embedded).

Everything is deterministic: run it again, get byte-identical output.

Usage: uv run python tableau/build_twb.py
"""

from __future__ import annotations

from pathlib import Path

SHEET_ID = "1SEiXqOMMtoUWezdZFc2l3cpsrDFmkWrvfN_x0k_AtaU"
DRIVE_URL = (f"https://www.googleapis.com/drive/v3/files/{SHEET_ID}/export"
             f"?mimeType=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
OUT = Path(__file__).parent / "fdic_peer_satellite.twb"

# ids mimic Desktop's 28-char lowercase-alnum format
DS_PEER = "federated.0fdicpeer0000000000000000000"
DS_TREND = "federated.0fdictrend000000000000000000"
CONN_PEER = "cloudfile:googledrive-excel-direct.0fdicpeerconn000000000000000"
CONN_TREND = "cloudfile:googledrive-excel-direct.0fdictrendconn00000000000000"
CALC_BEYOND = "Calculation_fdicbeyond2sigma0001"

FOOTER = ("Peer-relative statistics from public filings, never an assessment of any "
          "bank's condition. Source: FDIC BankFind Suite API. "
          "https://yugveerj.github.io/fdic-bank-health-monitor/")

# (name, caption, local-type, role) — remote types are refreshed on connect
PEER_COLS = [
    ("cert", "Cert", "integer", "dimension"),
    ("bank_name", "Bank name", "string", "dimension"),
    ("peer_band", "Peer band", "string", "dimension"),
    ("metric", "Metric", "string", "dimension"),
    ("value", "Value", "real", "measure"),
    ("robust_z", "Robust z", "real", "measure"),
    ("peer_median", "Peer median", "real", "measure"),
]
TREND_COLS = [
    ("cert", "Cert", "integer", "dimension"),
    ("bank_name", "Bank name", "string", "dimension"),
    ("report_date", "Report date", "date", "dimension"),
    ("peer_band", "Peer band", "string", "dimension"),
    ("business_model", "Business model", "string", "dimension"),
    ("total_assets_bn", "Total assets ($B)", "real", "measure"),
    ("roa_pct", "ROA %", "real", "measure"),
    ("net_interest_margin_pct", "Net interest margin %", "real", "measure"),
    ("equity_to_assets", "Equity / assets", "real", "measure"),
    ("uninsured_deposit_share", "Uninsured deposit share", "real", "measure"),
    ("brokered_deposit_share", "Brokered deposit share", "real", "measure"),
    ("securities_to_assets", "Securities / assets", "real", "measure"),
    ("loans_to_deposits", "Loans / deposits", "real", "measure"),
    ("efficiency_ratio_pct", "Efficiency ratio %", "real", "measure"),
    ("noncurrent_loans_ratio_pct", "Noncurrent loans %", "real", "measure"),
]


def connection_xml(conn_name: str, tab: str, cols: list, grid: str) -> str:
    col_lines = "\n".join(
        f"            <column datatype='string' name='{n}' ordinal='{i}' />"
        for i, (n, _, _, _) in enumerate(cols)
    )
    meta = "\n".join(f"""          <metadata-record class='column'>
            <remote-name>{n}</remote-name>
            <remote-type>130</remote-type>
            <local-name>[{n}]</local-name>
            <parent-name>[{tab}]</parent-name>
            <remote-alias>{n}</remote-alias>
            <ordinal>{i}</ordinal>
            <local-type>string</local-type>
            <aggregation>Count</aggregation>
            <contains-null>true</contains-null>
          </metadata-record>""" for i, (n, _, _, _) in enumerate(cols))
    return f"""      <connection class='federated'>
        <named-connections>
          <named-connection caption='FDIC Bank Health Monitor' name='{conn_name}'>
            <connection class='cloudfile:googledrive-excel-direct' cleaning='no' cloudFileExtension='xlsx' cloudFileId='{SHEET_ID}' cloudFileMetadata_-_folder='root' cloudFileName='FDIC Bank Health Monitor.xlsx' cloudFileProvider='googledrive' cloudFileRequestURL='{DRIVE_URL}' compat='no' dataRefreshTime='' interpretationMode='0' server-oauth='server-custom' validate='no' workgroup-auth-mode='prompt' />
          </named-connection>
        </named-connections>
        <relation connection='{conn_name}' name='{tab}' table='[&apos;{tab}$&apos;]' type='table'>
          <columns gridOrigin='{grid}' header='yes' outcome='2'>
{col_lines}
          </columns>
        </relation>
        <metadata-records>
{meta}
        </metadata-records>
      </connection>"""


def column_decls(cols: list) -> str:
    out = []
    for n, caption, ltype, role in cols:
        custom = " datatype-customized='true'" if ltype in ("real", "integer", "date") else ""
        vtype = ("quantitative" if role == "measure"
                 else "ordinal" if ltype in ("date", "integer") else "nominal")
        out.append(f"      <column caption='{caption}' datatype='{ltype}'{custom} "
                   f"name='[{n}]' role='{role}' type='{vtype}' />")
    return "\n".join(out)


def datasource_peer() -> str:
    return f"""    <datasource caption='peer_percentiles (FDIC)' inline='true' name='{DS_PEER}' version='18.1'>
{connection_xml(CONN_PEER, "peer_percentiles", PEER_COLS, "A1:G14456:no:A1:G14456:0")}
      <aliases enabled='yes' />
{column_decls(PEER_COLS)}
      <column caption='Beyond 2 robust sigma' datatype='boolean' name='[{CALC_BEYOND}]' role='dimension' type='nominal'>
        <calculation class='tableau' formula='ABS([robust_z]) &gt;= 2' />
      </column>
      <column-instance column='[peer_band]' derivation='None' name='[none:peer_band:nk]' pivot='key' type='nominal' />
      <column-instance column='[metric]' derivation='None' name='[none:metric:nk]' pivot='key' type='nominal' />
      <column-instance column='[bank_name]' derivation='None' name='[none:bank_name:nk]' pivot='key' type='nominal' />
      <column-instance column='[{CALC_BEYOND}]' derivation='User' name='[usr:{CALC_BEYOND}:nk]' pivot='key' type='nominal' />
      <column-instance column='[value]' derivation='Avg' name='[avg:value:qk]' pivot='key' type='quantitative' />
      <column-instance column='[robust_z]' derivation='Avg' name='[avg:robust_z:qk]' pivot='key' type='quantitative' />
      <column-instance column='[peer_median]' derivation='Avg' name='[avg:peer_median:qk]' pivot='key' type='quantitative' />
      <layout dim-ordering='alphabetic' dim-percentage='0.5' measure-ordering='alphabetic' measure-percentage='0.4' show-structure='true' />
      <style>
        <style-rule element='mark'>
          <encoding attr='color' field='[usr:{CALC_BEYOND}:nk]' type='palette'>
            <map to='#d73027'>
              <bucket>true</bucket>
            </map>
            <map to='#b0b7bd'>
              <bucket>false</bucket>
            </map>
          </encoding>
        </style-rule>
      </style>
    </datasource>"""


def datasource_trend() -> str:
    instances = [
        "      <column-instance column='[bank_name]' derivation='None' name='[none:bank_name:nk]' pivot='key' type='nominal' />",
        "      <column-instance column='[report_date]' derivation='None' name='[none:report_date:qk]' pivot='key' type='quantitative' />",
    ]
    for n, _, _ltype, role in TREND_COLS:
        if role == "measure":
            instances.append(f"      <column-instance column='[{n}]' derivation='Avg' "
                             f"name='[avg:{n}:qk]' pivot='key' type='quantitative' />")
    return f"""    <datasource caption='bank_trends (FDIC)' inline='true' name='{DS_TREND}' version='18.1'>
{connection_xml(CONN_TREND, "bank_trends", TREND_COLS, "A1:O12453:no:A1:O12453:0")}
      <aliases enabled='yes' />
{column_decls(TREND_COLS)}
{chr(10).join(instances)}
      <layout dim-ordering='alphabetic' dim-percentage='0.5' measure-ordering='alphabetic' measure-percentage='0.4' show-structure='true' />
    </datasource>"""


def dep_line(ds: str, cols: list, names: set) -> str:
    out = []
    for n, caption, ltype, role in cols:
        if n not in names:
            continue
        custom = " datatype-customized='true'" if ltype in ("real", "integer", "date") else ""
        vtype = ("quantitative" if role == "measure"
                 else "ordinal" if ltype in ("date", "integer") else "nominal")
        out.append(f"            <column caption='{caption}' datatype='{ltype}'{custom} "
                   f"name='[{n}]' role='{role}' type='{vtype}' />")
    return "\n".join(out)


def cat_filter(ds: str, instance: str, member: str, group: int) -> str:
    return f"""          <filter class='categorical' column='[{ds}].[{instance}]' filter-group='{group}'>
            <groupfilter function='member' level='[{instance}]' member='&quot;{member}&quot;' user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />
          </filter>"""


def worksheet_distribution() -> str:
    return f"""    <worksheet name='Distribution'>
      <table>
        <view>
          <datasources>
            <datasource caption='peer_percentiles (FDIC)' name='{DS_PEER}' />
          </datasources>
          <datasource-dependencies datasource='{DS_PEER}'>
{dep_line(DS_PEER, PEER_COLS, {"bank_name", "peer_band", "metric", "value", "robust_z", "peer_median"})}
            <column caption='Beyond 2 robust sigma' datatype='boolean' name='[{CALC_BEYOND}]' role='dimension' type='nominal'>
              <calculation class='tableau' formula='ABS([robust_z]) &gt;= 2' />
            </column>
            <column-instance column='[bank_name]' derivation='None' name='[none:bank_name:nk]' pivot='key' type='nominal' />
            <column-instance column='[peer_band]' derivation='None' name='[none:peer_band:nk]' pivot='key' type='nominal' />
            <column-instance column='[metric]' derivation='None' name='[none:metric:nk]' pivot='key' type='nominal' />
            <column-instance column='[{CALC_BEYOND}]' derivation='User' name='[usr:{CALC_BEYOND}:nk]' pivot='key' type='nominal' />
            <column-instance column='[value]' derivation='Avg' name='[avg:value:qk]' pivot='key' type='quantitative' />
            <column-instance column='[peer_median]' derivation='Avg' name='[avg:peer_median:qk]' pivot='key' type='quantitative' />
          </datasource-dependencies>
{cat_filter(DS_PEER, "none:peer_band:nk", "$1B-$10B", 3)}
{cat_filter(DS_PEER, "none:metric:nk", "uninsured_deposit_share", 4)}
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Circle' />
            <encodings>
              <color column='[{DS_PEER}].[usr:{CALC_BEYOND}:nk]' />
              <lod column='[{DS_PEER}].[none:bank_name:nk]' />
              <tooltip column='[{DS_PEER}].[avg:peer_median:qk]' />
            </encodings>
          </pane>
        </panes>
        <rows />
        <cols>[{DS_PEER}].[avg:value:qk]</cols>
      </table>
    </worksheet>"""


def worksheet_tails() -> str:
    return f"""    <worksheet name='Tails'>
      <table>
        <view>
          <datasources>
            <datasource caption='peer_percentiles (FDIC)' name='{DS_PEER}' />
          </datasources>
          <datasource-dependencies datasource='{DS_PEER}'>
{dep_line(DS_PEER, PEER_COLS, {"bank_name", "peer_band", "metric", "value", "robust_z"})}
            <column-instance column='[bank_name]' derivation='None' name='[none:bank_name:nk]' pivot='key' type='nominal' />
            <column-instance column='[peer_band]' derivation='None' name='[none:peer_band:nk]' pivot='key' type='nominal' />
            <column-instance column='[metric]' derivation='None' name='[none:metric:nk]' pivot='key' type='nominal' />
            <column-instance column='[value]' derivation='Avg' name='[avg:value:qk]' pivot='key' type='quantitative' />
            <column-instance column='[robust_z]' derivation='Avg' name='[avg:robust_z:qk]' pivot='key' type='quantitative' />
          </datasource-dependencies>
{cat_filter(DS_PEER, "none:peer_band:nk", "$1B-$10B", 3)}
{cat_filter(DS_PEER, "none:metric:nk", "uninsured_deposit_share", 4)}
          <filter class='quantitative' column='[{DS_PEER}].[avg:robust_z:qk]' included-values='in-range'>
            <min>2</min>
          </filter>
          <sort class='computed' column='[{DS_PEER}].[none:bank_name:nk]' direction='DESC' using='[{DS_PEER}].[avg:robust_z:qk]' />
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Text' />
            <encodings>
              <text column='[{DS_PEER}].[avg:robust_z:qk]' />
              <tooltip column='[{DS_PEER}].[avg:value:qk]' />
            </encodings>
          </pane>
        </panes>
        <rows>[{DS_PEER}].[none:bank_name:nk]</rows>
        <cols />
      </table>
    </worksheet>"""


def worksheet_trend(name: str, measures: list[str]) -> str:
    rows = " + ".join(f"[{DS_TREND}].[avg:{m}:qk]" for m in measures)
    if len(measures) > 1:
        rows = f"({rows})"
    deps = {"bank_name", "report_date"} | set(measures)
    inst = [
        "            <column-instance column='[bank_name]' derivation='None' name='[none:bank_name:nk]' pivot='key' type='nominal' />",
        "            <column-instance column='[report_date]' derivation='None' name='[none:report_date:qk]' pivot='key' type='quantitative' />",
    ] + [f"            <column-instance column='[{m}]' derivation='Avg' name='[avg:{m}:qk]' pivot='key' type='quantitative' />"
         for m in measures]
    return f"""    <worksheet name='{name}'>
      <table>
        <view>
          <datasources>
            <datasource caption='bank_trends (FDIC)' name='{DS_TREND}' />
          </datasources>
          <datasource-dependencies datasource='{DS_TREND}'>
{dep_line(DS_TREND, TREND_COLS, deps)}
{chr(10).join(inst)}
          </datasource-dependencies>
{cat_filter(DS_TREND, "none:bank_name:nk", "Silicon Valley Bank", 2)}
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='Line' />
          </pane>
        </panes>
        <rows>{rows}</rows>
        <cols>[{DS_TREND}].[none:report_date:qk]</cols>
      </table>
    </worksheet>"""


def zone_style() -> str:
    return """              <zone-style>
                <format attr='border-color' value='#000000' />
                <format attr='border-style' value='none' />
                <format attr='border-width' value='0' />
                <format attr='margin' value='4' />
              </zone-style>"""


def text_zone(zid: int, x: int, y: int, w: int, h: int) -> str:
    return f"""            <zone forceUpdate='true' h='{h}' id='{zid}' type-v2='text' w='{w}' x='{x}' y='{y}'>
              <formatted-text>
                <run fontcolor='#666666' fontname='Tableau Regular' fontsize='9'>{FOOTER}</run>
              </formatted-text>
{zone_style()}
            </zone>"""


def dashboard_explorer() -> str:
    return f"""    <dashboard name='Peer explorer'>
      <style />
      <size maxheight='900' maxwidth='1100' minheight='900' minwidth='1100' sizing-mode='fixed' />
      <datasources />
      <zones>
        <zone h='100000' id='20' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='96800' id='21' param='vert' type-v2='layout-flow' w='98700' x='650' y='1600'>
            <zone h='42000' id='22' param='horz' type-v2='layout-flow' w='98700' x='650' y='1600'>
              <zone h='42000' id='23' name='Distribution' show-title='true' w='72000' x='650' y='1600'>
{zone_style()}
              </zone>
              <zone fixed-size='200' h='42000' id='24' is-fixed='true' param='vert' type-v2='layout-flow' w='26700' x='72650' y='1600'>
                <zone h='14000' id='25' name='Distribution' param='[{DS_PEER}].[none:peer_band:nk]' type-v2='filter' w='26700' x='72650' y='1600'>
{zone_style()}
                </zone>
                <zone h='14000' id='26' name='Distribution' param='[{DS_PEER}].[none:metric:nk]' type-v2='filter' w='26700' x='72650' y='15600'>
{zone_style()}
                </zone>
                <zone h='14000' id='27' name='Distribution' pane-specification-id='0' param='[{DS_PEER}].[usr:{CALC_BEYOND}:nk]' type-v2='color' w='26700' x='72650' y='29600'>
{zone_style()}
                </zone>
              </zone>
            </zone>
            <zone h='48800' id='28' name='Tails' show-title='true' w='98700' x='650' y='43600'>
{zone_style()}
            </zone>
{text_zone(29, 650, 92400, 98700, 6000)}
          </zone>
          <zone-style>
            <format attr='border-color' value='#000000' />
            <format attr='border-style' value='none' />
            <format attr='border-width' value='0' />
            <format attr='margin' value='8' />
          </zone-style>
        </zone>
      </zones>
      <devicelayouts />
    </dashboard>"""


def dashboard_profile() -> str:
    return f"""    <dashboard name='Bank profile'>
      <style />
      <size maxheight='900' maxwidth='1100' minheight='900' minwidth='1100' sizing-mode='fixed' />
      <datasources />
      <zones>
        <zone h='100000' id='40' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='96800' id='41' param='vert' type-v2='layout-flow' w='98700' x='650' y='1600'>
            <zone fixed-size='80' h='8000' id='42' is-fixed='true' name='Trend - size and capital' param='[{DS_TREND}].[none:bank_name:nk]' type-v2='filter' w='98700' x='650' y='1600'>
{zone_style()}
            </zone>
            <zone h='41400' id='43' name='Trend - size and capital' show-title='true' w='98700' x='650' y='9600'>
{zone_style()}
            </zone>
            <zone h='41400' id='44' name='Trend - funding and margin' show-title='true' w='98700' x='650' y='51000'>
{zone_style()}
            </zone>
{text_zone(45, 650, 92400, 98700, 6000)}
          </zone>
          <zone-style>
            <format attr='border-color' value='#000000' />
            <format attr='border-style' value='none' />
            <format attr='border-width' value='0' />
            <format attr='margin' value='8' />
          </zone-style>
        </zone>
      </zones>
      <devicelayouts />
    </dashboard>"""


def windows() -> str:
    def ws_window(name: str, extra_cards: str = "") -> str:
        return f"""    <window class='worksheet' name='{name}'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'>
            <card type='columns' />
          </strip>
          <strip size='2147483647'>
            <card type='rows' />
          </strip>
        </edge>{extra_cards}
      </cards>
    </window>"""

    color_card = f"""
        <edge name='right'>
          <strip size='160'>
            <card pane-specification-id='0' param='[{DS_PEER}].[usr:{CALC_BEYOND}:nk]' type='color' />
          </strip>
        </edge>"""
    # no dashboard windows: the load schema demands (viewpoints, active,
    # device-preview) for those and Desktop synthesizes them anyway
    return "\n".join([
        ws_window("Distribution", color_card),
        ws_window("Tails"),
        ws_window("Trend - size and capital"),
        ws_window("Trend - funding and margin"),
    ])


def build() -> str:
    return f"""<?xml version='1.0' encoding='utf-8' ?>

<workbook original-version='18.1' source-build='2026.1.1 (20261.26.0410.0924)' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
  <datasources>
{datasource_peer()}
{datasource_trend()}
  </datasources>
  <worksheets>
{worksheet_distribution()}
{worksheet_tails()}
{worksheet_trend("Trend - size and capital", ["total_assets_bn", "equity_to_assets"])}
{worksheet_trend("Trend - funding and margin", ["uninsured_deposit_share", "brokered_deposit_share", "net_interest_margin_pct"])}
  </worksheets>
  <dashboards>
{dashboard_explorer()}
{dashboard_profile()}
  </dashboards>
  <windows source-height='51'>
{windows()}
  </windows>
</workbook>
"""


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
