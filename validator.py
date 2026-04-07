import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationError:
    row: int  # 1-based; header is row 0
    field: str
    reason: str


def validate_records(records: list[dict[str, str]]) -> list[ValidationError]:
    """Return all validation violations across *records*.

    Checks that `name` and `description` are non-empty for every record.
    An empty list means all records are valid.
    """
    errors: list[ValidationError] = []
    for i, record in enumerate(records, start=1):
        for field in ("name", "description"):
            if not record.get(field, "").strip():
                errors.append(ValidationError(row=i, field=field, reason="empty or whitespace-only"))
    return errors
