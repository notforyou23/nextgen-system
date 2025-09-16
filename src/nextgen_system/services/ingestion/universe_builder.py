"""Dynamic universe builder for next-generation system."""

from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set

import pandas as pd
import yfinance as yf

from nextgen_system.config import settings

logger = logging.getLogger(__name__)


@dataclass
class UniverseMetrics:
    symbol: str
    last_close: float
    avg_volume: float
    dollar_volume: float


def _cache_dir() -> Path:
    cache = Path(settings.get("paths", "data_dir")) / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _cache_file() -> Path:
    return _cache_dir() / f"universe_{datetime.now().strftime('%Y%m%d')}.json"


def _load_cache(hours: int) -> List[UniverseMetrics]:
    path = _cache_file()
    if not path.exists():
        return []
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    if age_hours > hours:
        return []
    try:
        payload = json.loads(path.read_text())
        metrics = []
        for item in payload:
            if not isinstance(item, dict) or not item.get("symbol"):
                continue
            metrics.append(
                UniverseMetrics(
                    symbol=item.get("symbol"),
                    last_close=float(item.get("last_close", 0.0)),
                    avg_volume=float(item.get("avg_volume", 0.0)),
                    dollar_volume=float(item.get("dollar_volume", 0.0)),
                )
            )
        return metrics
    except Exception:
        return []


def _save_cache(metrics: Sequence[UniverseMetrics]) -> None:
    try:
        payload = [
            {
                "symbol": m.symbol,
                "last_close": m.last_close,
                "avg_volume": m.avg_volume,
                "dollar_volume": m.dollar_volume,
            }
            for m in metrics
        ]
        _cache_file().write_text(json.dumps(payload))
    except Exception:
        logger.debug("Failed to write universe cache", exc_info=True)


def _fetch_table(url: str, **kwargs) -> List[str]:
    try:
        tables = pd.read_html(url, **kwargs)
    except Exception as exc:
        logger.warning("Failed to fetch table %s: %s", url, exc)
        return []
    symbols: List[str] = []
    for df in tables:
        for col in df.columns:
            if str(col).lower() in ("symbol", "ticker", "stock symbol"):
                series = df[col].astype(str).str.strip()
                symbols.extend(series.tolist())
                break
    return symbols


def _sp500_symbols() -> List[str]:
    return _fetch_table(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        storage_options={"User-Agent": "Mozilla/5.0"},
    )


def _nasdaq100_symbols() -> List[str]:
    return _fetch_table(
        "https://en.wikipedia.org/wiki/Nasdaq-100",
        attrs={"class": "wikitable"},
        header=0,
        storage_options={"User-Agent": "Mozilla/5.0"},
    )


def _supplemental_symbols() -> List[str]:
    # Hard-coded supplemental lists from legacy remain optional; aim to remove once
    # alternative data sources are plugged in. They broaden coverage beyond mega-cap tech.
    supplements = [
        'PLTR', 'SNOW', 'DDOG', 'CRWD', 'ZS', 'OKTA', 'PANW', 'MDB', 'ESTC', 'CFLT',
        'NET', 'ANET', 'TEAM', 'SHOP', 'DOCU', 'TWLO', 'PINS', 'RBLX', 'U', 'FVRR',
        'KRTX', 'RYTM', 'CRSP', 'EDIT', 'BEAM', 'VECT', 'GRCL', 'SANA', 'PMVP', 'MORF',
        'SOFI', 'AFRM', 'HOOD', 'COIN', 'SQ', 'PYPL', 'LC', 'UPST', 'LMND', 'OPEN',
        'ENPH', 'SEDG', 'FSLR', 'RUN', 'PLUG', 'BLDP', 'BE', 'NOVA', 'ARRY', 'FLNC',
        'SPCE', 'JOBY', 'ASTR', 'RDW', 'LUNR', 'ASTS', 'IONQ', 'RKLB',
        'RIVN', 'LI', 'NIO', 'BYDDY', 'LCID', 'NKLA', 'WKHS',
        'WELL', 'AVB', 'EQR', 'SPG', 'O', 'FRT', 'VTR', 'UDR', 'CPT', 'MAA',
        'XLK', 'XLF', 'XLV', 'XLE', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE',
        'ARKK', 'ARKQ', 'ARKW', 'ARKG', 'ARKF', 'ICLN', 'CLOU', 'ROBO', 'FINX', 'HACK',
        'TLT', 'IEF', 'SHY', 'LQD', 'HYG', 'EMB', 'TIP', 'VTEB', 'VGIT', 'VGSH'
    ]
    return supplements


def _compute_metrics(symbols: Iterable[str], min_price: float, min_volume: float) -> List[UniverseMetrics]:
    metrics: List[UniverseMetrics] = []
    for sym in symbols:
        try:
            t = sym
            if '.' in t and len(t.split('.')[-1]) == 1:
                t = t.replace('.', '-')
            hist = yf.Ticker(t).history(period='1mo', interval='1d', auto_adjust=True, prepost=False)
            if hist is None or hist.empty:
                continue
            close = float(hist['Close'].iloc[-1])
            if close < min_price:
                continue
            volume = float(hist['Volume'].tail(20).mean()) if 'Volume' in hist.columns else 0.0
            if volume < min_volume:
                continue
            metrics.append(
                UniverseMetrics(
                    symbol=sym,
                    last_close=close,
                    avg_volume=volume,
                    dollar_volume=close * volume,
                )
            )
        except Exception:
            continue
    return metrics


def build_universe(force_refresh: bool = False, target_size: Optional[int] = None) -> List[UniverseMetrics]:
    cfg = settings.get("ingestion", "universe", default={})
    if not cfg.get("dynamic", True):
        raise RuntimeError("Static universe not supported in next-gen configuration")

    cache_hours = cfg.get("cache_hours", 1)
    if not force_refresh:
        cached = _load_cache(cache_hours)
        if cached:
            return cached

    target = target_size if target_size is not None else cfg.get("target_size", 0)
    if target == 0:
        target = None

    symbols: Set[str] = set()
    symbols.update(_sp500_symbols())
    symbols.update(_nasdaq100_symbols())
    symbols.update(_supplemental_symbols())

    if not symbols:
        raise RuntimeError("Failed to fetch index symbols for universe")

    metrics = _compute_metrics(symbols, cfg.get("min_price", 1.0), cfg.get("min_avg_volume", 100000))
    if not metrics:
        fallback_symbols = cfg.get("familiar_symbols") or ["AAPL", "MSFT", "NVDA", "TSLA"]
        metrics = [
            UniverseMetrics(symbol=sym, last_close=100.0, avg_volume=1_000_000, dollar_volume=100_000_000)
            for sym in fallback_symbols
        ]

    familiar = set(cfg.get("familiar_symbols", []))
    exploration_ratio = cfg.get("exploration_ratio", 0.8)

    familiar_candidates = [m for m in metrics if m.symbol in familiar]
    exploration_candidates = [m for m in metrics if m.symbol not in familiar]

    random.seed(datetime.now().timestamp() * random.random())

    if target is None:
        exploration_count = len(exploration_candidates)
        familiar_count = len(familiar_candidates)
    else:
        exploration_count = int(target * exploration_ratio)
        familiar_count = max(0, target - exploration_count)

    random.shuffle(exploration_candidates)
    random.shuffle(familiar_candidates)

    selected: List[UniverseMetrics] = []
    selected.extend(exploration_candidates[:exploration_count])
    selected.extend(familiar_candidates[:familiar_count])

    # If we still need more (e.g., familiar list too small), fill from remaining exploration
    if target is not None and len(selected) < target:
        remaining = [m for m in metrics if m.symbol not in {s.symbol for s in selected}]
        random.shuffle(remaining)
        selected.extend(remaining[: target - len(selected)])

    random.shuffle(selected)
    _save_cache(selected)
    return selected
