from dataclasses import dataclass
from langchain_core.tools import tool
from typing import Optional
import yfinance as yf

PROXY_MAP = {
    "Global_Tech_Corp": "TSM",  
    "Global_Auto_Corp": "TM",   
}


@dataclass
class FinancialImpactReport:
    ticker: str
    proxy_for: Optional[str]
    risk_score: float
    margin_compression_bps: float
    baseline_eps: float
    stressed_eps: float
    eps_change_pct: float
    revenue: float
    net_income_impact: float
    current_price: float
    trailing_pe: Optional[float]
    naive_price_impact: Optional[float]      # P/E held constant
    stressed_price_impact: Optional[float]   # P/E also compresses slightly
    notes: str

    def __str__(self):
        lines = [
            f"--- Financial Impact: {self.ticker}"
            + (f" (proxy for {self.proxy_for})" if self.proxy_for else "")
            + " ---",
            f"Simulated exposure (R_v):        {self.risk_score:.2f}",
            f"Assumed margin compression:      {self.margin_compression_bps:.0f} bps (full-shock basis)",
            f"Revenue (TTM):                    ${self.revenue/1e9:.2f}B",
            f"Net income impact:               -${abs(self.net_income_impact)/1e6:.1f}M",
            f"EPS: {self.baseline_eps:.2f} -> {self.stressed_eps:.2f}  ({self.eps_change_pct:+.1f}%)",
        ]
        if self.trailing_pe:
            lines.append(f"Current price / trailing P/E:    ${self.current_price:.2f} / {self.trailing_pe:.1f}x")
        if self.naive_price_impact is not None:
            lines.append(f"Implied price impact (P/E flat): {self.naive_price_impact:+.1f}%")
        if self.stressed_price_impact is not None:
            lines.append(f"Implied price impact (P/E also compresses): {self.stressed_price_impact:+.1f}%")
        lines.append(f"Note: {self.notes}")
        return "\n".join(lines)


class FinancialImpactEstimator:
    def __init__(self, margin_compression_bps: float = 150.0, tax_rate: float = 0.21,
                 pe_compression_at_full_shock: float = 0.10):
        """
        margin_compression_bps: gross/operating margin hit (in bps) assumed
            under a FULL shock (R_v = 1.0). Scaled linearly by R_v below that.
        tax_rate: fallback effective tax rate if the ticker's own isn't available.
        pe_compression_at_full_shock: how much the trailing P/E itself derates
            under a full shock (e.g. 0.10 = multiple falls 10% at R_v=1.0),
            used only for the "stressed" price scenario.
        """
        self.margin_compression_bps = margin_compression_bps
        self.tax_rate = tax_rate
        self.pe_compression_at_full_shock = pe_compression_at_full_shock

    def estimate(self, ticker: str, risk_score: float, proxy_for: Optional[str] = None) -> FinancialImpactReport:
        t = yf.Ticker(ticker)
        info = t.info  

        revenue = info.get("totalRevenue")
        shares = info.get("sharesOutstanding")
        baseline_eps = info.get("trailingEps")
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        trailing_pe = info.get("trailingPE")
        effective_tax_rate = self.tax_rate  

        missing = [k for k, v in {
            "totalRevenue": revenue, "sharesOutstanding": shares,
            "trailingEps": baseline_eps, "currentPrice": current_price,
        }.items() if v is None]
        if missing:
            raise ValueError(f"{ticker}: missing fields from yfinance: {missing}. "
                              f"Data availability varies by ticker/market — verify manually.")

        effective_margin_hit = (self.margin_compression_bps / 10000.0) * max(0.0, min(1.0, risk_score))
        operating_income_impact = revenue * effective_margin_hit
        net_income_impact = -operating_income_impact * (1 - effective_tax_rate)
        eps_impact = net_income_impact / shares

        stressed_eps = baseline_eps + eps_impact
        eps_change_pct = (eps_impact / baseline_eps) * 100 if baseline_eps else float("nan")

        naive_price_impact = None
        stressed_price_impact = None
        if trailing_pe and current_price:
            naive_new_price = stressed_eps * trailing_pe
            naive_price_impact = (naive_new_price - current_price) / current_price * 100

            pe_hit = self.pe_compression_at_full_shock * max(0.0, min(1.0, risk_score))
            stressed_pe = trailing_pe * (1 - pe_hit)
            stressed_new_price = stressed_eps * stressed_pe
            stressed_price_impact = (stressed_new_price - current_price) / current_price * 100

        return FinancialImpactReport(
            ticker=ticker,
            proxy_for=proxy_for,
            risk_score=risk_score,
            margin_compression_bps=self.margin_compression_bps,
            baseline_eps=baseline_eps,
            stressed_eps=stressed_eps,
            eps_change_pct=eps_change_pct,
            revenue=revenue,
            net_income_impact=net_income_impact,
            current_price=current_price,
            trailing_pe=trailing_pe,
            naive_price_impact=naive_price_impact,
            stressed_price_impact=stressed_price_impact,
            notes="Directional sensitivity only — assumes constant tax rate, no management "
                  "offset, and no second-order demand effects. Not investment advice.",
        )

    def estimate_from_graph_node(self, node_name: str, risk_score: float) -> FinancialImpactReport:
        """Convenience wrapper for graph node names that have a PROXY_MAP entry."""
        ticker = PROXY_MAP.get(node_name)
        if not ticker:
            raise KeyError(f"No proxy ticker mapped for node '{node_name}'. "
                            f"Add it to PROXY_MAP.")
        return self.estimate(ticker, risk_score, proxy_for=node_name)


if __name__ == "__main__":
    sample_risk_scores = {"Global_Tech_Corp": 0.42, "Global_Auto_Corp": 0.18}

    fie = FinancialImpactEstimator(margin_compression_bps=150, tax_rate=0.21)
    for node, r_v in sample_risk_scores.items():
        try:
            report = fie.estimate_from_graph_node(node, r_v)
            print(report)
            print()
        except Exception as e:
            print(f"[{node}] Could not fetch data: {e}\n")


@tool
def estimate_financial_impact(node_name: str, risk_score: float) -> str:
    """Given a graph node with a mapped stock ticker (see PROXY_MAP) and its
    simulated risk score, return the estimated EPS and share-price impact
    using live market data. Call this after stimulate_supply_chain_shock
    when the user wants dollar/percentage terms, not just a risk score."""
    estimator = FinancialImpactEstimator()
    try:
        return str(estimator.estimate_from_graph_node(node_name, risk_score))
    except (KeyError, ValueError) as e:
        return f"Could not estimate financial impact: {e}"