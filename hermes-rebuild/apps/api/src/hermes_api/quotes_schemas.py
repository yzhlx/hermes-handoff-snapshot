"""HTTP contracts for the daily quote and personal quote library."""

from pydantic import BaseModel, ConfigDict


class QuoteData(BaseModel):
    id: str
    text: str
    author: str | None = None


class QuotePreferenceData(BaseModel):
    quote_id: str
    text: str
    favorited: bool
    disliked: bool
    version: int
    updated_at: str


class DailyQuoteData(BaseModel):
    local_date: str
    day_timezone: str
    quote: QuoteData | None
    reason: str | None = None
    preference: QuotePreferenceData | None = None


class QuoteTodayData(BaseModel):
    daily_quote: DailyQuoteData


class QuotePreferenceResultData(BaseModel):
    preference: QuotePreferenceData
    daily_quote: DailyQuoteData | None = None


class QuoteFavoritesData(BaseModel):
    items: list[QuotePreferenceData]
    disliked: list[QuotePreferenceData]
    next_cursor: str | None = None


class QuotePreferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    favorited: bool
    disliked: bool
