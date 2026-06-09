from dataclasses import dataclass, field


@dataclass(frozen=True)
class NoticeLink:
    title: str
    url: str


@dataclass(frozen=True)
class Notice:
    title: str
    url: str
    notice_type: str
    publish_date: str | None = None
    region: str | None = None
    buyer: str | None = None
    budget: float | None = None
    deadline: str | None = None
    content: str = ""
    category_code: str | None = None
    source_column: str | None = None
    source_column_path: str | None = None
    source_category_code: str | None = None


@dataclass(frozen=True)
class ClassificationResult:
    primary_category: str
    secondary_categories: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    is_media_relevant: bool = False
    tier: str = "excluded"
    confidence: str = "low"


@dataclass(frozen=True)
class OpportunityCard:
    notice: Notice
    classification: ClassificationResult
    opportunity_class: str
    reasons: list[str]
    risks: list[str]
    recommended_action: str
    missing_fields: list[str] = field(default_factory=list)
