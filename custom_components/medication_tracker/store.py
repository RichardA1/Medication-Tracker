"""Storage handler for Medication Tracker."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    ATTR_DATE_ADDED,
    ATTR_DAYS,
    ATTR_DOSE_QUANTITY,
    ATTR_DOSAGE,
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
    DEFAULT_DOSE_QUANTITY,
    DEFAULT_QUANTITY,
    DEFAULT_REFILL_THRESHOLD,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class MedicationStore:
    """Wraps HA's Store helper with full async CRUD for medications and schedules."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {"medications": {}}

    async def async_load(self) -> None:
        """Load persisted data from .storage."""
        stored = await self._store.async_load()
        if stored:
            self._data = stored
        _LOGGER.debug("Loaded %d medication(s) from storage", len(self.get_medications()))

    async def async_save(self) -> None:
        """Persist current data to .storage."""
        await self._store.async_save(self._data)

    # ── Medication Read ────────────────────────────────────────────────────────

    def get_medications(self) -> dict[str, Any]:
        """Return all medications keyed by UUID."""
        return self._data.get("medications", {})

    def get_medication(self, med_id: str) -> dict[str, Any] | None:
        """Return a single medication by ID, or None if not found."""
        return self._data.get("medications", {}).get(med_id)

    # ── Medication Create ──────────────────────────────────────────────────────

    async def async_add_medication(
        self,
        name: str,
        dosage: str,
        instructions: str,
        quantity: float,
        refill_threshold: float,
        image: str,
    ) -> dict[str, Any]:
        """Add a new medication and persist to storage."""
        med_id = str(uuid.uuid4())
        medication = {
            ATTR_ID: med_id,
            ATTR_NAME: name,
            ATTR_DOSAGE: dosage,
            ATTR_INSTRUCTIONS: instructions,
            ATTR_QUANTITY: quantity,
            ATTR_REFILL_THRESHOLD: refill_threshold,
            ATTR_IMAGE: image,
            ATTR_DATE_ADDED: datetime.now().isoformat(),
            ATTR_SCHEDULES: {},
        }
        self._data.setdefault("medications", {})[med_id] = medication
        await self.async_save()
        _LOGGER.debug("Added medication '%s %s' (%s)", name, dosage, med_id)
        return medication

    # ── Medication Update ──────────────────────────────────────────────────────

    async def async_update_medication(
        self,
        med_id: str,
        name: str,
        dosage: str,
        instructions: str,
        quantity: float,
        refill_threshold: float,
        image: str,
    ) -> dict[str, Any] | None:
        """Update all editable fields of an existing medication. Returns None if not found."""
        medications = self._data.get("medications", {})
        if med_id not in medications:
            _LOGGER.warning("Cannot update: medication %s not found", med_id)
            return None
        medications[med_id].update(
            {
                ATTR_NAME: name,
                ATTR_DOSAGE: dosage,
                ATTR_INSTRUCTIONS: instructions,
                ATTR_QUANTITY: quantity,
                ATTR_REFILL_THRESHOLD: refill_threshold,
                ATTR_IMAGE: image,
            }
        )
        # Ensure legacy records without a schedules key are migrated silently.
        medications[med_id].setdefault(ATTR_SCHEDULES, {})
        await self.async_save()
        _LOGGER.debug("Updated medication '%s %s' (%s)", name, dosage, med_id)
        return medications[med_id]

    async def async_set_quantity(
        self, med_id: str, quantity: float
    ) -> dict[str, Any] | None:
        """Set quantity on hand to an absolute value. Returns None if not found."""
        medications = self._data.get("medications", {})
        if med_id not in medications:
            _LOGGER.warning("Cannot set quantity: medication %s not found", med_id)
            return None
        medications[med_id][ATTR_QUANTITY] = quantity
        await self.async_save()
        _LOGGER.debug(
            "Set quantity for '%s' to %s",
            medications[med_id].get(ATTR_NAME, med_id),
            quantity,
        )
        return medications[med_id]

    async def async_take_dose(
        self, med_id: str, dose_quantity: float
    ) -> dict[str, Any] | None:
        """Subtract dose_quantity from the medication's quantity on hand.

        Quantity is floored at 0 — it cannot go negative.
        Returns the updated medication dict, or None if not found.
        """
        medications = self._data.get("medications", {})
        if med_id not in medications:
            _LOGGER.warning("Cannot take dose: medication %s not found", med_id)
            return None
        current = float(medications[med_id].get(ATTR_QUANTITY, 0))
        medications[med_id][ATTR_QUANTITY] = max(0.0, current - dose_quantity)
        await self.async_save()
        _LOGGER.debug(
            "Took dose of %s for '%s': %s -> %s",
            dose_quantity,
            medications[med_id].get(ATTR_NAME, med_id),
            current,
            medications[med_id][ATTR_QUANTITY],
        )
        return medications[med_id]

    async def async_add_quantity(
        self, med_id: str, quantity: float
    ) -> dict[str, Any] | None:
        """Add quantity to the medication's current quantity on hand (for refills).

        Returns the updated medication dict, or None if not found.
        """
        medications = self._data.get("medications", {})
        if med_id not in medications:
            _LOGGER.warning("Cannot add quantity: medication %s not found", med_id)
            return None
        current = float(medications[med_id].get(ATTR_QUANTITY, 0))
        medications[med_id][ATTR_QUANTITY] = current + quantity
        await self.async_save()
        _LOGGER.debug(
            "Added %s to '%s': %s -> %s",
            quantity,
            medications[med_id].get(ATTR_NAME, med_id),
            current,
            medications[med_id][ATTR_QUANTITY],
        )
        return medications[med_id]

    # ── Medication Delete ──────────────────────────────────────────────────────

    async def async_delete_medication(self, med_id: str) -> bool:
        """Delete a medication and all its schedules. Returns False if not found."""
        medications = self._data.get("medications", {})
        if med_id not in medications:
            _LOGGER.warning("Cannot delete: medication %s not found", med_id)
            return False
        name = medications[med_id].get(ATTR_NAME, med_id)
        del medications[med_id]
        await self.async_save()
        _LOGGER.debug("Deleted medication '%s' (%s)", name, med_id)
        return True

    # ── Schedule Read ──────────────────────────────────────────────────────────

    def get_schedules(self, med_id: str) -> dict[str, Any]:
        """Return all schedules for a medication, keyed by schedule UUID."""
        med = self.get_medication(med_id)
        if med is None:
            return {}
        return med.get(ATTR_SCHEDULES, {})

    def get_schedule(self, med_id: str, schedule_id: str) -> dict[str, Any] | None:
        """Return a single schedule by ID, or None if not found."""
        return self.get_schedules(med_id).get(schedule_id)

    # ── Schedule Create ────────────────────────────────────────────────────────

    async def async_add_schedule(
        self,
        med_id: str,
        days: list[str],
        time: str,
        dose_quantity: float,
        enabled: bool,
    ) -> dict[str, Any] | None:
        """Add a new schedule to a medication. Returns None if medication not found."""
        medications = self._data.get("medications", {})
        if med_id not in medications:
            _LOGGER.warning("Cannot add schedule: medication %s not found", med_id)
            return None
        schedule_id = str(uuid.uuid4())
        schedule = {
            ATTR_SCHEDULE_ID: schedule_id,
            ATTR_DAYS: days,
            ATTR_TIME: time,
            ATTR_DOSE_QUANTITY: dose_quantity,
            ATTR_ENABLED: enabled,
        }
        medications[med_id].setdefault(ATTR_SCHEDULES, {})[schedule_id] = schedule
        await self.async_save()
        _LOGGER.debug(
            "Added schedule %s to '%s' (%s): %s at %s",
            schedule_id,
            medications[med_id].get(ATTR_NAME, med_id),
            med_id,
            days,
            time,
        )
        return schedule

    # ── Schedule Update ────────────────────────────────────────────────────────

    async def async_update_schedule(
        self,
        med_id: str,
        schedule_id: str,
        days: list[str],
        time: str,
        dose_quantity: float,
        enabled: bool,
    ) -> dict[str, Any] | None:
        """Update an existing schedule. Returns None if medication or schedule not found."""
        medications = self._data.get("medications", {})
        if med_id not in medications:
            _LOGGER.warning("Cannot update schedule: medication %s not found", med_id)
            return None
        schedules = medications[med_id].get(ATTR_SCHEDULES, {})
        if schedule_id not in schedules:
            _LOGGER.warning(
                "Cannot update schedule: schedule %s not found on medication %s",
                schedule_id,
                med_id,
            )
            return None
        schedules[schedule_id].update(
            {
                ATTR_DAYS: days,
                ATTR_TIME: time,
                ATTR_DOSE_QUANTITY: dose_quantity,
                ATTR_ENABLED: enabled,
            }
        )
        await self.async_save()
        _LOGGER.debug("Updated schedule %s on medication %s", schedule_id, med_id)
        return schedules[schedule_id]

    # ── Schedule Delete ────────────────────────────────────────────────────────

    async def async_delete_schedule(self, med_id: str, schedule_id: str) -> bool:
        """Delete a schedule from a medication. Returns False if not found."""
        medications = self._data.get("medications", {})
        if med_id not in medications:
            _LOGGER.warning(
                "Cannot delete schedule: medication %s not found", med_id
            )
            return False
        schedules = medications[med_id].get(ATTR_SCHEDULES, {})
        if schedule_id not in schedules:
            _LOGGER.warning(
                "Cannot delete schedule: schedule %s not found on medication %s",
                schedule_id,
                med_id,
            )
            return False
        del schedules[schedule_id]
        await self.async_save()
        _LOGGER.debug("Deleted schedule %s from medication %s", schedule_id, med_id)
        return True
