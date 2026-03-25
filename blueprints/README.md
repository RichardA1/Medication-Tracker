# 🤖 Medication Tracker — Automation Blueprints

This directory contains Home Assistant automation blueprints for the
[Medication Tracker](../README.md) custom integration.

---

## 📋 Available Blueprints

| Blueprint | Domain | Description |
|---|---|---|
| [medication_reminder.yaml](automation/medication_tracker/medication_reminder.yaml) | `automation` | TTS announcement on smart speakers at scheduled dose times |

---

## 💊 `medication_reminder` — Scheduled TTS Reminder

### Overview

This blueprint creates an automation that:

1. **Polls every minute** using a `time_pattern` trigger.
2. **Checks** all selected medication sensors for an enabled schedule whose
   `days` list includes today and whose `time` matches the current `HH:MM`.
3. **Announces** a personalised message on your smart speakers via TTS — the
   announcement is rendered from a Jinja2 template and includes the
   medication name, dosage, usage instructions, and remaining quantity.
4. **Appends a low-stock warning** (optional) when the medication's
   `low_stock` attribute is `true`.
5. **Auto-logs the dose** (optional) by calling
   `medication_tracker.take_dose`, deducting the schedule's `dose_quantity`
   from the medication's on-hand stock.

### Minimum Requirements

| Requirement | Minimum Version |
|---|---|
| Home Assistant Core | 2024.1.0 |
| Medication Tracker | 1.0.0 |
| A `tts.*` integration | any current |
| A `media_player` entity | any |

> **TTS options:**  
> - `tts.google_translate` — built-in, free, no account required.  
> - `tts.nabu_casa_cloud_tts` — higher quality, requires HA Cloud subscription.  
> - `tts.piper` — local neural TTS, requires the Piper add-on.  
> - Any other TTS integration that exposes a `tts.*` entity and supports `tts.speak`.

### Installation

#### Option A — Import via URL (easiest)

1. In Home Assistant, open **Settings → Automations & Scenes → Blueprints**.
2. Click **Import Blueprint** (bottom-right).
3. Paste the raw URL:
   ```
   https://raw.githubusercontent.com/YOUR_USERNAME/medication-tracker/main/blueprints/automation/medication_tracker/medication_reminder.yaml
   ```
4. Click **Preview** then **Import Blueprint**.

#### Option B — Manual file copy

1. Download
   [`medication_reminder.yaml`](automation/medication_tracker/medication_reminder.yaml).
2. Place it in your Home Assistant config directory at:
   ```
   config/blueprints/automation/medication_tracker/medication_reminder.yaml
   ```
3. Reload blueprints: **Developer Tools → YAML → Reload → Automation Blueprints**
   (or restart HA).

---

### Configuration

After importing, create an automation from the blueprint:

**Settings → Automations & Scenes → Blueprints → Medication Tracker — Scheduled TTS Reminder → Create Automation**

#### Input Fields

| Field | Required | Default | Description |
|---|---|---|---|
| **Medication Sensor(s)** | ✅ | — | One or more `sensor.*` entities from the Medication Tracker integration. Add every medication you want this automation to handle. |
| **TTS Engine** | ✅ | — | Your `tts.*` entity (e.g. `tts.google_translate`). |
| **Smart Speaker(s)** | ✅ | — | One or more `media_player` entities to announce on. All speak simultaneously. |
| **Announcement Message** | ✅ | See below | Jinja2 template for the spoken message. |
| **Append Low Stock Warning** | ➖ | `true` | Adds a refill reminder when stock is low. |
| **Low Stock Message** | ➖ | See below | Template appended when `low_stock` is `true`. |
| **Auto-Log Dose** | ➖ | `true` | Calls `take_dose` to deduct stock automatically. |
| **Pre-Announcement Delay** | ➖ | `0` | Seconds to wait before speaking (0–60). |

---

### Message Templates

Templates are rendered in Jinja2. The following variables are available
inside both the **Announcement Message** and **Low Stock Message** fields:

| Variable | Type | Example |
|---|---|---|
| `{{ med_name }}` | string | `Metformin` |
| `{{ dosage }}` | string | `500mg tablet` |
| `{{ instructions }}` | string | `Take with food` |
| `{{ quantity }}` | float | `14.0` |
| `{{ dose_quantity }}` | float | `1.0` |
| `{{ schedule_time }}` | string | `08:00` |

#### Default announcement (rendered example)

> *"Medication reminder. Time to take your Metformin. 500mg tablet. Take with
> food. You have 14 doses remaining."*

#### Default low stock suffix (rendered example)

> *"Warning: Metformin is running low. Only 5 remaining. Please arrange a
> refill soon."*

#### Custom template examples

**Simple:**
```
Time to take {{ med_name }}!
```

**With conditional dosage detail:**
```
{{ med_name }} reminder.
{% if dose_quantity != 1.0 %}Take {{ dose_quantity | int }} tablets.{% endif %}
{% if instructions | trim %}Remember: {{ instructions }}.{% endif %}
```

**Friendly countdown:**
```
Hey! Don't forget your {{ med_name }} — {{ dosage }}.
{% if quantity | int <= 7 %}
Heads up, you only have {{ quantity | int }} left. Refill time soon!
{% endif %}
```

---

### Multi-Medication Setup

Add all of your medication sensors to the **Medication Sensor(s)** field in a
single automation. The blueprint iterates over every sensor and fires for any
schedule that matches the current time. This means:

- **08:00 — Metformin** fires → one TTS announcement for Metformin.
- **08:00 — Lisinopril** fires → one TTS announcement for Lisinopril.
- Both happen automatically within the same automation run.

You can also create **separate automations** per medication (e.g. different
speakers, different messages) — just create multiple automations from the
same blueprint.

---

### Multi-Speaker Announcements

Select multiple speakers in the **Smart Speaker(s)** field. All will announce
simultaneously via a single `tts.speak` call. The `tts.speak` service accepts
a list of `media_player_entity_id` values natively.

---

### Auto-Logging Doses

When **Auto-Log Dose** is enabled, the blueprint calls:

```yaml
service: medication_tracker.take_dose
data:
  item_id: "{{ item_id }}"        # UUID from sensor's item_id attribute
  dose_quantity: "{{ dose_quantity }}"  # from the schedule definition
```

This matches the `dose_quantity` defined on each schedule, so if a schedule
is set to deduct `2.0` doses at once, that is what will be subtracted.

To **manually log doses instead**, disable **Auto-Log Dose** and call the
service from a button card or a separate automation.

---

### Example: YAML Automation (Advanced)

If you prefer to manage automations in YAML, here is a generated example
for a single medication with a Google Home speaker:

```yaml
alias: Metformin Morning Reminder
description: Announces Metformin reminder at scheduled time and logs the dose.
use_blueprint:
  path: medication_tracker/medication_reminder.yaml
  input:
    medication_sensors:
      - sensor.metformin_500mg
    tts_entity: tts.google_translate
    media_players:
      - media_player.kitchen_speaker
      - media_player.bedroom_speaker
    announcement_template: >-
      Medication reminder.
      Time to take your {{ med_name }}.
      {%- if dosage | trim %} {{ dosage }}.{% endif %}
      {%- if instructions | trim %} {{ instructions }}.{% endif %}
      You have {{ quantity | int }} doses remaining.
    low_stock_warning: true
    low_stock_template: >-
      Warning: {{ med_name }} is running low.
      Only {{ quantity | int }} remaining. Please arrange a refill soon.
    auto_take_dose: true
    pre_announce_delay: 3
```

---

### Troubleshooting

**The automation fires but I hear nothing on my speaker.**
- Check that the selected `tts.*` entity is working: run a manual `tts.speak`
  call from Developer Tools.
- Some speakers (Google Home, Echo) need to be actively on the same local
  network and not in "do not disturb" mode.
- Try increasing **Pre-Announcement Delay** to 3–5 seconds.

**The automation does not fire at the scheduled time.**
- Confirm the schedule is set correctly: open the sensor in Developer Tools
  and inspect the `schedules` attribute — check `enabled: true`, correct
  `days`, and `time` in `HH:MM:SS` format.
- Verify the `time_pattern` trigger is active: check the automation's trace
  in **Settings → Automations → [your automation] → Traces**.
- Make sure your HA server's timezone is set correctly
  (**Settings → System → General → Time Zone**).

**The dose is not being deducted from stock.**
- Ensure **Auto-Log Dose** is enabled.
- Check the `item_id` attribute on the sensor — it should be a UUID string.
- Look for errors in **Settings → System → Logs** filtered by
  `medication_tracker`.

**I want different messages for different medications.**
- Create one automation from this blueprint per medication (or per group of
  medications that should share a message style).

---

## 🤝 Contributing

Blueprint contributions are welcome! Please open an issue or pull request
in the main repository. See [CONTRIBUTING.md](../CONTRIBUTING.md) for
guidelines.

---

<p align="center">Part of the <a href="../README.md">Medication Tracker</a> project for Home Assistant</p>
