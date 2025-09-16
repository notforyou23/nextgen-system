"""Local trading prioritizer that ranks tickers by recent predictions."""

from __future__ import annotations

from typing import List, Optional

from nextgen_system.persistence.database import get_database, Database


class PrioritizerAdapter:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_database()

    def prioritized_tickers(self, max_tickers: int = 10) -> List[str]:
        ranked = self.db.fetch_all(
            """
            SELECT ticker
            FROM predictions
            ORDER BY confidence DESC, probability DESC
            LIMIT ?
            """,
            (max_tickers,),
        )
        tickers = [row[0] for row in ranked]
        if len(tickers) >= max_tickers:
            return tickers

        remaining = max_tickers - len(tickers)
        universe_rows = self.db.fetch_all(
            """
            SELECT ticker
            FROM ticker_universe
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (max(remaining, 0),),
        )
        for row in universe_rows:
            symbol = row[0]
            if symbol not in tickers:
                tickers.append(symbol)
            if len(tickers) >= max_tickers:
                break
        return tickers


__all__ = ["PrioritizerAdapter"]
