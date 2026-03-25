"""Config flow for Medication Tracker."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    ATTR_DAYS,
    ATTR_DOSAGE,
    ATTR_DOSE_QUANTITY,
    ATTR_ENABLED,
    ATTR_IMAGE,
    ATTR_INSTRUCTIONS,
    ATTR_NAME,
    ATTR_QUANTITY,
    ATTR_REFILL_THRESHOLD,
    ATTR_TIME,
    DAY_ABBREVIATIONS,
    DAYS_OF_WEEK,
    DEFAULT_DOSE_QUANTITY,
    DEFAULT_QUANTITY,
    DEFAULT_REFILL_THRESHOLD,
    DEFAULT_SCHEDULE_TIME,
    DOMAIN,
)
from .store import MedicationStore

_LOGGER = logging.getLogger(__name__)

# Day-of-week options for the multi-select selector — ordered Mon→Sun.
_DAY_OPTIONS = [
    {"label": DAY_ABBREVIATIONS[d], "value": d} for d in DAYS_OF_WEEK
]


def _get_store(hass, entry_id) -> MedicationStore:
    """Retrieve the MedicationStore for a given config entry."""
    return hass.data[DOMAIN][entry_id]


def _medication_schema(defaults: dict | None = None) -> vol.Schema:
    """Voluptuous schema shared by add and edit medication forms."""
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(ATTR_NAME, default=d.get(ATTR_NAME, "")): selector.selector(
                {"text": {"type": "text"}}
            ),
            vol.Required(ATTR_DOSAGE, default=d.get(ATTR_DOSAGE, "")): selector.selector(
                {"text": {"type": "text"}}
            ),
            vol.Optional(
                ATTR_INSTRUCTIONS, default=d.get(ATTR_INSTRUCTIONS, "")
            ): selector.selector({"text": {"multiline": True}}),
            vol.Optional(
                ATTR_QUANTITY, default=d.get(ATTR_QUANTITY, DEFAULT_QUANTITY)
            ): selector.selector(
                {"number": {"min": 0, "max": 99999, "step": 0.5, "mode": "box"}}
            ),
            vol.Optional(
                ATTR_REFILL_THRESHOLD,
                default=d.get(ATTR_REFILL_THRESHOLD, DEFAULT_REFILL_THRESHOLD),
            ): selector.selector(
                {"number": {"min": 0, "max": 99999, "step": 0.5, "mode": "box"}}
            ),
            vol.Optional(ATTR_IMAGE, default=d.get(ATTR_IMAGE, "")): selector.selector(
                {"text": {"type": "text"}}
            ),
        }
    )


def _schedule_schema(defaults: dict | None = None) -> vol.Schema:
    """Voluptuous schema shared by add and edit schedule forms."""
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(ATTR_DAYS, default=d.get(ATTR_DAYS, [])): selector.selector(
                {
                    "select": {
                        "options": _DAY_OPTIONS,
                        "multiple": True,
                        "mode": "list",
                    }
                }
            ),
            vol.Required(
                ATTR_TIME, default=d.get(ATTR_TIME, DEFAULT_SCHEDULE_TIME)
            ): selector.selector({"time": {}}),
            vol.Optional(
                ATTR_DOSE_QUANTITY,
                default=d.get(ATTR_DOSE_QUANTITY, DEFAULT_DOSE_QUANTITY),
            ): selector.selector(
                {"number": {"min": 0.5, "max": 99999, "step": 0.5, "mode": "box"}}
            ),
            vol.Optional(
                ATTR_ENABLED, default=d.get(ATTR_ENABLED, True)
            ): selector.selector({"boolean": {}}),
        }
    )


def _schedule_label(schedule: dict) -> str:
    """Format a human-readable label for a schedule dropdown option.

    Example: "Mon, Wed, Fri at 8:00 AM — 1.0 dose"
             "Daily at 9:00 PM — 2.0 doses [disabled]"
    """
    days = schedule.get(ATTR_DAYS, [])
    time_str = schedule.get(ATTR_TIME, "")
    dose = schedule.get(ATTR_DOSE_QUANTITY, DEFAULT_DOSE_QUANTITY)
    enabled = schedule.get(ATTR_ENABLED, True)

    sorted_days = sorted(days, key=lambda d: DAYS_OF_WEEK.index(d) if d in DAYS_OF_WEEK else 99)
    if len(sorted_days) == 7:
        days_str = "Daily"
    else:
        days_str = ", ".join(DAY_ABBREVIATIONS.get(d, d) for d in sorted_days)

    # Convert "HH:MM:SS" to "H:MM AM/PM"
    try:
        parts = time_str.split(":")
        hour, minute = int(parts[0]), int(parts[1])
        period = "AM" if hour < 12 else "PM"
        display_hour = hour % 12 or 12
        time_display = f"{display_hour}:{minute:02d} {period}"
    except (IndexError, ValueError):
        time_display = time_str or "?"

    dose_word = "dose" if dose == 1.0 else "doses"
    label = f"{days_str} at {time_display} — {dose} {dose_word}"
    if not enabled:
        label += " [disabled]"
    return label


# ── Config flow ────────────────────────────────────────────────────────────────

class MedicationTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Initial setup flow — creates a named tracker instance."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            title = user_input.get("title", "").strip()
            if not title:
                errors["title"] = "title_required"
            else:
                await self.async_set_unique_id(title.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data={"title": title})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("title", default="Medications"): selector.selector(
                        {"text": {"type": "text"}}
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow handler."""
        return MedicationTrackerOptionsFlow(config_entry)


# ── Options flow ───────────────────────────────────────────────────────────────

class MedicationTrackerOptionsFlow(config_entries.OptionsFlow):
    """Options flow — add, edit, and delete medications and schedules."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry_id = config_entry.entry_id
        self._selected_id: str | None = None          # selected medication UUID
        self._selected_schedule_id: str | None = None  # selected schedule UUID

    # ── Main menu ─────────────────────────────────────────────────────────────

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Show the main menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "add_medication",
                "edit_medication",
                "delete_medication",
                "add_schedule",
                "edit_schedule",
                "delete_schedule",
            ],
        )

    # ══ Medication CRUD ═══════════════════════════════════════════════════════

    # ── Add medication ────────────────────────────────────────────────────────

    async def async_step_add_medication(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a new medication."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(ATTR_NAME, "").strip()
            dosage = user_input.get(ATTR_DOSAGE, "").strip()
            if not name:
                errors[ATTR_NAME] = "name_required"
            elif not dosage:
                errors[ATTR_DOSAGE] = "dosage_required"
            else:
                store = _get_store(self.hass, self._entry_id)
                await store.async_add_medication(
                    name=name,
                    dosage=dosage,
                    instructions=user_input.get(ATTR_INSTRUCTIONS, "").strip(),
                    quantity=float(user_input.get(ATTR_QUANTITY, DEFAULT_QUANTITY)),
                    refill_threshold=float(
                        user_input.get(ATTR_REFILL_THRESHOLD, DEFAULT_REFILL_THRESHOLD)
                    ),
                    image=user_input.get(ATTR_IMAGE, "").strip(),
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_medication",
            data_schema=_medication_schema(),
            errors=errors,
        )

    # ── Edit medication — step 1: pick ────────────────────────────────────────

    async def async_step_edit_medication(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user select which medication to edit."""
        store = _get_store(self.hass, self._entry_id)
        medications = store.get_medications()
        if not medications:
            return self.async_abort(reason="no_medications")
        if user_input is not None:
            self._selected_id = user_input["med_id"]
            return await self.async_step_edit_medication_details()
        options = [
            {"label": f"{med[ATTR_NAME]} — {med[ATTR_DOSAGE]}", "value": mid}
            for mid, med in medications.items()
        ]
        return self.async_show_form(
            step_id="edit_medication",
            data_schema=vol.Schema(
                {vol.Required("med_id"): selector.selector({"select": {"options": options}})}
            ),
        )

    # ── Edit medication — step 2: form ────────────────────────────────────────

    async def async_step_edit_medication_details(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle editing the selected medication's fields."""
        store = _get_store(self.hass, self._entry_id)
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(ATTR_NAME, "").strip()
            dosage = user_input.get(ATTR_DOSAGE, "").strip()
            if not name:
                errors[ATTR_NAME] = "name_required"
            elif not dosage:
                errors[ATTR_DOSAGE] = "dosage_required"
            else:
                await store.async_update_medication(
                    med_id=self._selected_id,
                    name=name,
                    dosage=dosage,
                    instructions=user_input.get(ATTR_INSTRUCTIONS, "").strip(),
                    quantity=float(user_input.get(ATTR_QUANTITY, DEFAULT_QUANTITY)),
                    refill_threshold=float(
                        user_input.get(ATTR_REFILL_THRESHOLD, DEFAULT_REFILL_THRESHOLD)
                    ),
                    image=user_input.get(ATTR_IMAGE, "").strip(),
                )
                return self.async_create_entry(title="", data={})

        current = store.get_medication(self._selected_id) or {}
        return self.async_show_form(
            step_id="edit_medication_details",
            data_schema=_medication_schema(current),
            errors=errors,
        )

    # ── Delete medication ─────────────────────────────────────────────────────

    async def async_step_delete_medication(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle deleting a medication (and all its schedules) with confirmation."""
        store = _get_store(self.hass, self._entry_id)
        medications = store.get_medications()
        if not medications:
            return self.async_abort(reason="no_medications")
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("confirm"):
                errors["confirm"] = "confirm_required"
            else:
                await store.async_delete_medication(user_input["med_id"])
                return self.async_create_entry(title="", data={})
        options = [
            {"label": f"{med[ATTR_NAME]} — {med[ATTR_DOSAGE]}", "value": mid}
            for mid, med in medications.items()
        ]
        return self.async_show_form(
            step_id="delete_medication",
            data_schema=vol.Schema(
                {
                    vol.Required("med_id"): selector.selector({"select": {"options": options}}),
                    vol.Required("confirm", default=False): selector.selector({"boolean": {}}),
                }
            ),
            errors=errors,
            description_placeholders={"warning": "This cannot be undone."},
        )

    # ══ Schedule CRUD ══════════════════════════════════════════════════════════

    # ── Add schedule — step 1: pick medication ────────────────────────────────

    async def async_step_add_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which medication to add a schedule to."""
        store = _get_store(self.hass, self._entry_id)
        medications = store.get_medications()
        if not medications:
            return self.async_abort(reason="no_medications")
        if user_input is not None:
            self._selected_id = user_input["med_id"]
            return await self.async_step_add_schedule_details()
        options = [
            {"label": f"{med[ATTR_NAME]} — {med[ATTR_DOSAGE]}", "value": mid}
            for mid, med in medications.items()
        ]
        return self.async_show_form(
            step_id="add_schedule",
            data_schema=vol.Schema(
                {vol.Required("med_id"): selector.selector({"select": {"options": options}})}
            ),
        )

    # ── Add schedule — step 2: form ───────────────────────────────────────────

    async def async_step_add_schedule_details(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Fill in the new schedule's days, time, dose, and enabled flag."""
        errors: dict[str, str] = {}

        if user_input is not None:
            days = user_input.get(ATTR_DAYS, [])
            time = user_input.get(ATTR_TIME, "").strip()
            if not days:
                errors[ATTR_DAYS] = "days_required"
            elif not time:
                errors[ATTR_TIME] = "time_required"
            else:
                store = _get_store(self.hass, self._entry_id)
                await store.async_add_schedule(
                    med_id=self._selected_id,
                    days=days,
                    time=time,
                    dose_quantity=float(
                        user_input.get(ATTR_DOSE_QUANTITY, DEFAULT_DOSE_QUANTITY)
                    ),
                    enabled=bool(user_input.get(ATTR_ENABLED, True)),
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_schedule_details",
            data_schema=_schedule_schema(),
            errors=errors,
        )

    # ── Edit schedule — step 1: pick medication ───────────────────────────────

    async def async_step_edit_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which medication to edit a schedule on."""
        store = _get_store(self.hass, self._entry_id)
        medications = store.get_medications()
        if not medications:
            return self.async_abort(reason="no_medications")
        if user_input is not None:
            self._selected_id = user_input["med_id"]
            return await self.async_step_edit_schedule_select()
        options = [
            {"label": f"{med[ATTR_NAME]} — {med[ATTR_DOSAGE]}", "value": mid}
            for mid, med in medications.items()
        ]
        return self.async_show_form(
            step_id="edit_schedule",
            data_schema=vol.Schema(
                {vol.Required("med_id"): selector.selector({"select": {"options": options}})}
            ),
        )

    # ── Edit schedule — step 2: pick schedule ─────────────────────────────────

    async def async_step_edit_schedule_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which schedule to edit."""
        store = _get_store(self.hass, self._entry_id)
        schedules = store.get_schedules(self._selected_id)
        if not schedules:
            return self.async_abort(reason="no_schedules")
        if user_input is not None:
            self._selected_schedule_id = user_input["schedule_id"]
            return await self.async_step_edit_schedule_details()
        options = [
            {"label": _schedule_label(sched), "value": sid}
            for sid, sched in schedules.items()
        ]
        return self.async_show_form(
            step_id="edit_schedule_select",
            data_schema=vol.Schema(
                {
                    vol.Required("schedule_id"): selector.selector(
                        {"select": {"options": options}}
                    )
                }
            ),
        )

    # ── Edit schedule — step 3: form ──────────────────────────────────────────

    async def async_step_edit_schedule_details(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the selected schedule's fields."""
        store = _get_store(self.hass, self._entry_id)
        errors: dict[str, str] = {}

        if user_input is not None:
            days = user_input.get(ATTR_DAYS, [])
            time = user_input.get(ATTR_TIME, "").strip()
            if not days:
                errors[ATTR_DAYS] = "days_required"
            elif not time:
                errors[ATTR_TIME] = "time_required"
            else:
                await store.async_update_schedule(
                    med_id=self._selected_id,
                    schedule_id=self._selected_schedule_id,
                    days=days,
                    time=time,
                    dose_quantity=float(
                        user_input.get(ATTR_DOSE_QUANTITY, DEFAULT_DOSE_QUANTITY)
                    ),
                    enabled=bool(user_input.get(ATTR_ENABLED, True)),
                )
                return self.async_create_entry(title="", data={})

        current = store.get_schedule(self._selected_id, self._selected_schedule_id) or {}
        return self.async_show_form(
            step_id="edit_schedule_details",
            data_schema=_schedule_schema(current),
            errors=errors,
        )

    # ── Delete schedule — step 1: pick medication ─────────────────────────────

    async def async_step_delete_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select which medication to delete a schedule from."""
        store = _get_store(self.hass, self._entry_id)
        medications = store.get_medications()
        if not medications:
            return self.async_abort(reason="no_medications")
        if user_input is not None:
            self._selected_id = user_input["med_id"]
            return await self.async_step_delete_schedule_confirm()
        options = [
            {"label": f"{med[ATTR_NAME]} — {med[ATTR_DOSAGE]}", "value": mid}
            for mid, med in medications.items()
        ]
        return self.async_show_form(
            step_id="delete_schedule",
            data_schema=vol.Schema(
                {vol.Required("med_id"): selector.selector({"select": {"options": options}})}
            ),
        )

    # ── Delete schedule — step 2: pick schedule + confirm ────────────────────

    async def async_step_delete_schedule_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select a schedule and confirm deletion."""
        store = _get_store(self.hass, self._entry_id)
        schedules = store.get_schedules(self._selected_id)
        if not schedules:
            return self.async_abort(reason="no_schedules")
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input.get("confirm"):
                errors["confirm"] = "confirm_required"
            else:
                await store.async_delete_schedule(
                    self._selected_id, user_input["schedule_id"]
                )
                return self.async_create_entry(title="", data={})
        options = [
            {"label": _schedule_label(sched), "value": sid}
            for sid, sched in schedules.items()
        ]
        return self.async_show_form(
            step_id="delete_schedule_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required("schedule_id"): selector.selector(
                        {"select": {"options": options}}
                    ),
                    vol.Required("confirm", default=False): selector.selector({"boolean": {}}),
                }
            ),
            errors=errors,
            description_placeholders={"warning": "This cannot be undone."},
        )
