"""Sensor platform for Medication Tracker."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, time as dt_time
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_DATE_ADDED,
    ATTR_DAYS,
    ATTR_DOSAGE,
    ATTR_DOSE_QUANTITY,
    ATTR_ENABLED,
    ATTR_ID,
    ATTR_IMAGE,
    ATTR_INSTRUCTIONS,
    ATTR_NAME,
    ATTR_QUANTITY,
    ATTR_REFILL_THRESHOLD,
    ATTR_SCHEDULE_ID,
    ATTR_SCHEDULES,
    ATTR_TIME,
    DAYS_OF_WEEK,
    DOMAIN,
    SIGNAL_MEDICATION_UPDATED,
)
from .store import MedicationStore

_LOGGER = logging.getLogger(__name__)


def _compute_next_dose_time(schedules: dict[str, Any]) -> str | None:
    """Return the ISO timestamp of the next upcoming scheduled dose.

    Iterates all enabled schedules and looks up to 7 days ahead to find the
    earliest future dose time. Returns None if no enabled schedules exist or
    none have days/time populated.
    """
    now = datetime.now()
    today_idx = now.weekday()  # 0 = Monday, 6 = Sunday

    earliest: datetime | None = None

    for schedule in schedules.values():
        if not schedule.get(ATTR_ENABLED, True):
            continue
        days: list[str] = schedule.get(ATTR_DAYS, [])
        time_str: str = schedule.get(ATTR_TIME, "")
        if not days or not time_str:
            continue

        try:
            parts = time_str.split(":")
            hour, minute = int(parts[0]), int(parts[1])
        except (IndexError, ValueError):
            continue

        # Check today through the next 7 days for the soonest occurrence.
        for offset in range(8):
            check_idx = (today_idx + offset) % 7
            check_day = DAYS_OF_WEEK[check_idx]
            if check_day in days:
                candidate_date = (now + timedelta(days=offset)).date()
                candidate = datetime.combine(candidate_date, dt_time(hour, minute))
                if candidate > now:
                    if earliest is None or candidate < earliest:
                        earliest = candidate
                break  # found the next occurrence for this schedule; move on

    return earliest.isoformat() if earliest else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one MedicationSensor per stored medication."""
    store: MedicationStore = hass.data[DOMAIN][entry.entry_id]
    entities = [
        MedicationSensor(entry, medication)
        for medication in store.get_medications().values()
    ]
    async_add_entities(entities, update_before_add=True)
    _LOGGER.debug("Set up %d medication sensor(s)", len(entities))


class MedicationSensor(SensorEntity):
    """A sensor representing a single tracked medication.

    State        : current quantity on hand (float).
    Name         : "Medication Dosage" — e.g. "Metformin 500mg".
    Attributes   : name, dosage, instructions, quantity, refill_threshold,
                   low_stock, schedules, next_dose_time, photo_path,
                   item_id, date_added.
    entity_picture: returns photo path for HA entity thumbnails.
    Icon         : mdi:pill normally; mdi:pill-off when low_stock is true.

    Subscribes to SIGNAL_MEDICATION_UPDATED via HA's dispatcher so that
    take_dose, add_quantity, and set_quantity service calls update the sensor
    state live without requiring a Home Assistant restart.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, medication: dict[str, Any]) -> None:
        self._entry = entry
        self._medication = medication
        self._attr_unique_id = f"medication_tracker_{medication[ATTR_ID]}"
        self._attr_name = self._build_name(medication)

    @staticmethod
    def _build_name(medication: dict[str, Any]) -> str:
        """Combine name and dosage into a single display name."""
        name = medication.get(ATTR_NAME, "")
        dosage = medication.get(ATTR_DOSAGE, "")
        return f"{name} {dosage}".strip()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def async_added_to_hass(self) -> None:
        """Subscribe to dispatcher signals when the entity is added to HA."""
        med_id = self._medication[ATTR_ID]
        signal = SIGNAL_MEDICATION_UPDATED.format(
            entry_id=self._entry.entry_id, med_id=med_id
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, self._handle_update)
        )

    @callback
    def _handle_update(self, updated_medication: dict[str, Any]) -> None:
        """Receive an updated medication dict and push new state to HA."""
        self._medication = updated_medication
        self._attr_name = self._build_name(updated_medication)
        self.async_write_ha_state()

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def native_value(self) -> float:
        """Return the current quantity on hand."""
        return float(self._medication.get(ATTR_QUANTITY, 0))

    # ── Picture ───────────────────────────────────────────────────────────────

    @property
    def entity_picture(self) -> str | None:
        """Return the photo path for the HA entity thumbnail."""
        path = self._medication.get(ATTR_IMAGE, "")
        return path if path else None

    # ── Attributes ────────────────────────────────────────────────────────────

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose full medication details as entity attributes.

        Includes a serialised schedule list and a computed next_dose_time
        so that dashboards and automations can consume schedule data without
        needing to read raw storage.
        """
        quantity = float(self._medication.get(ATTR_QUANTITY, 0))
        refill_threshold = float(self._medication.get(ATTR_REFILL_THRESHOLD, 0))
        low_stock = refill_threshold > 0 and quantity <= refill_threshold

        raw_schedules: dict[str, Any] = self._medication.get(ATTR_SCHEDULES, {})

        # Serialise schedules as a flat list for easy template access.
        schedules_list = [
            {
                "schedule_id": s.get(ATTR_SCHEDULE_ID),
                "days": s.get(ATTR_DAYS, []),
                "time": s.get(ATTR_TIME, ""),
                "dose_quantity": s.get(ATTR_DOSE_QUANTITY, 1.0),
                "enabled": s.get(ATTR_ENABLED, True),
            }
            for s in raw_schedules.values()
        ]

        return {
            "item_id": self._medication.get(ATTR_ID),
            "name": self._medication.get(ATTR_NAME),
            "dosage": self._medication.get(ATTR_DOSAGE, ""),
            "instructions": self._medication.get(ATTR_INSTRUCTIONS, ""),
            "quantity": quantity,
            "refill_threshold": refill_threshold,
            "low_stock": low_stock,
            "schedules": schedules_list,
            "next_dose_time": _compute_next_dose_time(raw_schedules),
            "photo_path": self._medication.get(ATTR_IMAGE, ""),
            "date_added": self._medication.get(ATTR_DATE_ADDED),
        }

    # ── Device ────────────────────────────────────────────────────────────────

    @property
    def device_info(self) -> DeviceInfo:
        """Group all sensors under one device per tracker instance."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Custom Integration",
            model="Medication Tracker",
        )

    # ── Icon ──────────────────────────────────────────────────────────────────

    @property
    def icon(self) -> str:
        """Return mdi:pill normally; mdi:pill-off when stock is low."""
        quantity = float(self._medication.get(ATTR_QUANTITY, 0))
        refill_threshold = float(self._medication.get(ATTR_REFILL_THRESHOLD, 0))
        if refill_threshold > 0 and quantity <= refill_threshold:
            return "mdi:pill-off"
        return "mdi:pill"
