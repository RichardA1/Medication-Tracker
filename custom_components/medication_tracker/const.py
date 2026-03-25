"""Constants for Medication Tracker."""
DOMAIN = "medication_tracker"
STORAGE_KEY = f"{DOMAIN}.medications"
STORAGE_VERSION = 1

# ── Medication attribute keys ──────────────────────────────────────────────────
ATTR_ID = "id"
ATTR_NAME = "name"
ATTR_DOSAGE = "dosage"
ATTR_INSTRUCTIONS = "instructions"
ATTR_QUANTITY = "quantity"
ATTR_REFILL_THRESHOLD = "refill_threshold"
ATTR_IMAGE = "image"
ATTR_DATE_ADDED = "date_added"
ATTR_SCHEDULES = "schedules"

# ── Schedule attribute keys ────────────────────────────────────────────────────
ATTR_SCHEDULE_ID = "schedule_id"
ATTR_DAYS = "days"
ATTR_TIME = "time"
ATTR_DOSE_QUANTITY = "dose_quantity"
ATTR_ENABLED = "enabled"

# ── Days of week (stored values; order matters for display sorting) ────────────
DAYS_OF_WEEK = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

DAY_ABBREVIATIONS: dict[str, str] = {
    "monday": "Mon",
    "tuesday": "Tue",
    "wednesday": "Wed",
    "thursday": "Thu",
    "friday": "Fri",
    "saturday": "Sat",
    "sunday": "Sun",
}

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_QUANTITY = 0.0
DEFAULT_REFILL_THRESHOLD = 0.0
DEFAULT_DOSE_QUANTITY = 1.0
DEFAULT_SCHEDULE_TIME = "08:00:00"

# ── Service names ─────────────────────────────────────────────────────────────
SERVICE_SET_QUANTITY = "set_quantity"
SERVICE_TAKE_DOSE = "take_dose"
SERVICE_ADD_QUANTITY = "add_quantity"

# ── Dispatcher signal — format with entry_id and med_id ───────────────────────
SIGNAL_MEDICATION_UPDATED = f"{DOMAIN}_updated_{{entry_id}}_{{med_id}}"
