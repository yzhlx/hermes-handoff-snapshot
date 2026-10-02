"""Wire contracts for the independently loaded home sections."""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from .quotes_schemas import QuoteTodayData
from .records_schemas import RecordData, SummaryTextItem
from .schemas import SessionData, SubjectsData
from .suggestion_schemas import SuggestionData

HomeSectionName = Literal[
    "quote", "subjects", "continue_learning", "suggestions", "methods", "changes", "review"
]


class HomeSection[T](BaseModel):
    status: Literal["ready", "empty", "unavailable"]
    data: T | None = None
    source_revision: str | None = None
    error: "HomeSectionError | None" = None


class HomeSectionError(BaseModel):
    code: str
    message: str


class HomeContinueData(BaseModel):
    current: SessionData | None
    last: RecordData | None


class HomeSuggestionsData(BaseModel):
    items: list[SuggestionData]
    has_more: bool


class HomeMethodSummary(BaseModel):
    id: str
    title: str
    summary: str
    content_version: int


class HomeMethodsData(BaseModel):
    items: list[HomeMethodSummary]


class HomeChangesData(BaseModel):
    from_date: date
    to_date: date
    items: list[SummaryTextItem]
    effective_learning_days: int
    rule_version: str
    source_revision: str


class HomeReviewData(BaseModel):
    items: list[SuggestionData]
    has_more: bool


class HomeData(BaseModel):
    date: date
    timezone: str
    rule_version: str
    sections: "HomeSections"


class HomeSections(BaseModel):
    quote: HomeSection[QuoteTodayData] | None = None
    subjects: HomeSection[SubjectsData] | None = None
    continue_learning: HomeSection[HomeContinueData] | None = None
    suggestions: HomeSection[HomeSuggestionsData] | None = None
    methods: HomeSection[HomeMethodsData] | None = None
    changes: HomeSection[HomeChangesData] | None = None
    review: HomeSection[HomeReviewData] | None = None


HomeQuoteSection = HomeSection[QuoteTodayData]
HomeSubjectsSection = HomeSection[SubjectsData]
HomeContinueSection = HomeSection[HomeContinueData]
HomeSuggestionsSection = HomeSection[HomeSuggestionsData]
HomeMethodsSection = HomeSection[HomeMethodsData]
HomeChangesSection = HomeSection[HomeChangesData]
HomeReviewSection = HomeSection[HomeReviewData]
