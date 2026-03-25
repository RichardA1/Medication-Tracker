"""Medication Tracker integration for Home Assistant."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ATTR_DOSE_QUANTITY,
    ATTR_QUANTITY,
    DEFAULT_DOSE_QUANTITY,
    DOMAIN,
    SERVICE_ADD_QUANTITY,
    SERVICE_SET_QUANTITY,
    SERVICE_TAKE_DOSE,
    SIGNAL_MEDICATION_UPDATED,
)
from .store import MedicationStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

# ── Service schemas ────────────────────────────────────────────────────────────

SERVICE_SET_QUANTITY_SCHEMA = vol.Schema(
    {
        vol.Required("item_id"): cv.string,
        vol.Required(ATTR_QUANTITY): vol.All(vol.Coerce(float), vol.Range(min=0)),
    }
)

SERVICE_TAKE_DOSE_SCHEMA = vol.Schema(
    {
        vol.Required("item_id"): cv.string,
        vol.Optional(ATTR_DOSE_QUANTITY, default=DEFAULT_DOSE_QUANTITY): vol.All(
            vol.Coerce(float), vol.Range(min=0.5)
        ),
    }
)

SERVICE_ADD_QUANTITY_SCHEMA = vol.Schema(
    {
        vol.Required("item_id"): cv.string,
        vol.Required(ATTR_QUANTITY): vol.All(vol.Coerce(float), vol.Range(min=0)),
    }
)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _fire_medication_update(
    hass: HomeAssistant,
    entry_id: str,
    med_id: str,
    result: dict,
) -> None:
    """Fire a SIGNAL_MEDICATION_UPDATED dispatcher signal for a medication.

    This causes the corresponding MedicationSensor to call
    async_write_ha_state() immediately — no restart required.
    """
    signal = SIGNAL_MEDICATION_UPDATED.format(entry_id=entry_id, med_id=med_id)
    async_dispatcher_send(hass, signal, result)


async def _find_and_update(
    hass: HomeAssistant,
    med_id: str,
    store_method: str,
    log_prefix: str,
    **kwargs,
) -> bool:
    """Search all active MedicationStore instances for med_id, call store_method,
    and fire a dispatcher update. Returns True if the medication was found."""
    for entry_id, entry_store in hass.data[DOMAIN].items():
        if not isinstance(entry_store, MedicationStore):
            continue
        method = getattr(entry_store, store_method)
        result = await method(med_id, **kwargs)
        if result is not None:
            _fire_medication_update(hass, entry_id, med_id, result)
            _LOGGER.info(
                "%s '%s' (%s) -> quantity now %s",
                log_prefix,
                result.get("name", med_id),
                med_id,
                result.get(ATTR_QUANTITY),
            )
            return True
    _LOGGER.warning("%s: medication %s not found in any tracker instance", log_prefix, med_id)
    return False


# ── Setup / teardown ───────────────────────────────────────────────────────────

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Medication Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    store = MedicationStore(hass)
    await store.async_load()
    hass.data[DOMAIN][entry.entry_id] = store

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Services are registered once and shared across all tracker instances.
    if not hass.services.has_service(DOMAIN, SERVICE_SET_QUANTITY):
        _register_services(hass)

    _LOGGER.info(
        "Medication Tracker '%s' loaded with %d medication(s)",
        entry.title,
        len(store.get_medications()),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Medication Tracker config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    # Remove services only when the last tracker instance is removed.
    if not hass.data.get(DOMAIN):
        for service in (SERVICE_SET_QUANTITY, SERVICE_TAKE_DOSE, SERVICE_ADD_QUANTITY):
            hass.services.async_remove(DOMAIN, service)
            _LOGGER.debug("Removed service %s.%s", DOMAIN, service)

    return unload_ok


# ── Service registration ───────────────────────────────────────────────────────

def _register_services(hass: HomeAssistant) -> None:
    """Register all Medication Tracker services."""

    async def handle_set_quantity(call: ServiceCall) -> None:
        """Set a medication's quantity on hand to an absolute value.

        Use this to correct stock after a manual count or after editing
        a dispensing record. Fires a live dispatcher update.

        Fields:
            item_id  (str)   — UUID from the sensor's item_id attribute.
            quantity (float) — New quantity on hand (must be ≥ 0).
        """
        await _find_and_update(
            hass,
            med_id=call.data["item_id"],
            store_method="async_set_quantity",
            log_prefix="set_quantity",
            quantity=call.data[ATTR_QUANTITY],
        )

    async def handle_take_dose(call: ServiceCall) -> None:
        """Subtract a dose from a medication's quantity on hand.

        Quantity is floored at 0 — it can never go negative. Call this from
        a time-based automation at each scheduled dose time, or from a
        dashboard button after taking a pill. Fires a live dispatcher update.

        Fields:
            item_id       (str)   — UUID from the sensor's item_id attribute.
            dose_quantity (float) — Amount to subtract. Defaults to 1.0.
                                    Use the schedule's dose_quantity here.
        """
        await _find_and_update(
            hass,
            med_id=call.data["item_id"],
            store_method="async_take_dose",
            log_prefix="take_dose",
            dose_quantity=call.data.get(ATTR_DOSE_QUANTITY, DEFAULT_DOSE_QUANTITY),
        )

    async def handle_add_quantity(call: ServiceCall) -> None:
        """Add quantity to a medication's current stock on hand (for refills).

        Call this after picking up a prescription to add the dispensed
        quantity to current stock. Fires a live dispatcher update.

        Fields:
            item_id  (str)   — UUID from the sensor's item_id attribute.
            quantity (float) — Quantity to add (must be ≥ 0).
        """
        await _find_and_update(
            hass,
            med_id=call.data["item_id"],
            store_method="async_add_quantity",
            log_prefix="add_quantity",
            quantity=call.data[ATTR_QUANTITY],
        )

    hass.services.async_register(
        DOMAIN, SERVICE_SET_QUANTITY, handle_set_quantity,
        schema=SERVICE_SET_QUANTITY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_TAKE_DOSE, handle_take_dose,
        schema=SERVICE_TAKE_DOSE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_QUANTITY, handle_add_quantity,
        schema=SERVICE_ADD_QUANTITY_SCHEMA,
    )
    _LOGGER.debug(
        "Registered services: %s, %s, %s",
        SERVICE_SET_QUANTITY,
        SERVICE_TAKE_DOSE,
        SERVICE_ADD_QUANTITY,
    )
