# 💊 Medication Tracker for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/yourusername/medication-tracker.svg)](https://github.com/yourusername/medication-tracker/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Issues](https://img.shields.io/github/issues/yourusername/medication-tracker.svg)](https://github.com/yourusername/medication-tracker/issues)
[![Maintained](https://img.shields.io/badge/Maintained-yes-green.svg)](https://github.com/yourusername/medication-tracker/graphs/commit-activity)

A Home Assistant custom integration for tracking medications, dosages, usage schedules, and on-hand quantities — with optional photo support. Built as a fork of the [Item-Tracker](https://github.com/yourusername/item-tracker) project and designed for households managing one or more people's medication routines.

---

## 📋 Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Requirements](#requirements)
- [Installation](#installation)
  - [HACS (Recommended)](#hacs-recommended)
  - [Manual Installation](#manual-installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Adding a Medication](#adding-a-medication)
  - [Recording a Dose](#recording-a-dose)
  - [Updating Stock](#updating-stock)
- [Entities Created](#entities-created)
- [Automations & Blueprints](#automations--blueprints)
- [Lovelace Dashboard Cards](#lovelace-dashboard-cards)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## ✨ Features

- **Add Medications** with a name, brand/generic toggle, and optional notes
- **Dosage Tracking** — record strength (mg, mcg, mL, units, etc.) and form (tablet, capsule, liquid, patch, injection, etc.)
- **Usage / Schedule Information** — frequency, time of day, instructions (take with food, avoid sunlight, etc.)
- **On-Hand Quantity** — track how many pills, mL, or doses remain; get low-stock alerts
- **Optional Photo** — attach a photo of the medication label or packaging for easy identification
- **Multi-Person Support** — assign medications to individual household members / patient profiles
- **Refill Reminders** — configurable threshold triggers an automation-ready sensor
- **Dose Logging** — log each dose taken with a timestamp, enabling history tracking
- **Home Assistant Native** — creates sensors, binary sensors, and input fields fully compatible with automations, dashboards, and the HA Companion App
- **HACS Compatible** — easy install and updates via the Home Assistant Community Store

---

## 📸 Screenshots

> _Screenshots and dashboard previews will be added as the UI is finalized. Contributions welcome!_

---

## 🔧 Requirements

| Requirement | Minimum Version |
|---|---|
| Home Assistant Core | 2024.1.0 |
| Python | 3.11 |
| HACS (optional) | 1.34.0 |

No external dependencies, cloud accounts, or APIs are required. All data is stored locally within Home Assistant.

---

## 📦 Installation

### HACS (Recommended)

1. Open **HACS** in your Home Assistant sidebar.
2. Click **Integrations** → **⋮ Menu** → **Custom Repositories**.
3. Add the URL `https://github.com/yourusername/medication-tracker` and select **Integration** as the category.
4. Search for **Medication Tracker** and click **Download**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → + Add Integration** and search for **Medication Tracker**.

### Manual Installation

1. Download the [latest release](https://github.com/yourusername/medication-tracker/releases/latest).
2. Copy the `custom_components/medication_tracker` folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → + Add Integration** and search for **Medication Tracker**.

---

## ⚙️ Configuration

Medication Tracker is configured entirely through the **Home Assistant UI** — no manual YAML editing is required for basic use.

After installation and adding the integration, you can access the configuration panel from:

> **Settings → Devices & Services → Medication Tracker → Configure**

### Optional YAML Configuration

Advanced users can configure additional options in `configuration.yaml`:

```yaml
medication_tracker:
  # Default low-stock threshold (number of doses remaining before alert)
  low_stock_threshold: 7

  # Enable dose history logging
  enable_dose_log: true

  # Maximum number of dose log entries to retain per medication
  log_retention: 90

  # Path for medication photos (relative to /config/www/)
  photo_path: "medication_tracker/photos"
```

---

## 🚀 Usage

### Adding a Medication

1. Navigate to the **Medication Tracker** panel in the sidebar (or via Settings).
2. Click **+ Add Medication**.
3. Fill in the form:

| Field | Description | Required |
|---|---|---|
| **Name** | Medication name (e.g., "Metformin") | ✅ |
| **Brand / Generic** | Toggle between brand and generic name | ✅ |
| **Dosage Strength** | Numeric value (e.g., `500`) | ✅ |
| **Dosage Unit** | mg, mcg, mL, units, IU, etc. | ✅ |
| **Form** | Tablet, capsule, liquid, patch, injection, etc. | ✅ |
| **Frequency** | Once daily, twice daily, as needed, etc. | ✅ |
| **Time(s) of Day** | Morning, noon, evening, bedtime | ✅ |
| **Special Instructions** | Take with food, avoid alcohol, etc. | ➖ |
| **Quantity on Hand** | Number of doses, pills, or mL currently available | ✅ |
| **Refill Threshold** | Alert when quantity drops below this number | ➖ |
| **Assigned To** | Household member / patient profile | ➖ |
| **Photo** | Upload an image of the label or packaging | ➖ |
| **Notes** | Any additional information | ➖ |

4. Click **Save**. The medication is now tracked and entities are created automatically.

---

### Recording a Dose

- From the Medication Tracker panel, click the medication card and tap **Log Dose**.
- Alternatively, call the service from an automation or script:

```yaml
service: medication_tracker.log_dose
data:
  medication_id: "metformin_500mg"
  taken_at: "{{ now() }}"
  notes: "Taken with breakfast"
```

---

### Updating Stock

- From the medication card, click **Update Quantity** to set the current on-hand count.
- Or use the service:

```yaml
service: medication_tracker.update_quantity
data:
  medication_id: "metformin_500mg"
  quantity: 30
```

---

## 🔌 Entities Created

For each medication added, the integration creates the following entities:

| Entity | Type | Description |
|---|---|---|
| `sensor.{name}_quantity` | Sensor | Current quantity on hand |
| `binary_sensor.{name}_low_stock` | Binary Sensor | `on` when quantity ≤ threshold |
| `sensor.{name}_last_dose` | Sensor | Timestamp of last logged dose |
| `sensor.{name}_doses_today` | Sensor | Number of doses logged today |
| `input_text.{name}_instructions` | Input Text | Special usage instructions |
| `input_text.{name}_dosage` | Input Text | Dosage strength and form |

---

## 🤖 Automations & Blueprints

### Example: Low Stock Notification

```yaml
alias: "Medication Low Stock Alert"
trigger:
  - platform: state
    entity_id: binary_sensor.metformin_500mg_low_stock
    to: "on"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "💊 Refill Reminder"
      message: >
        {{ state_attr('sensor.metformin_500mg_quantity', 'friendly_name') }}
        is running low. Only
        {{ states('sensor.metformin_500mg_quantity') }} doses remaining.
```

### Example: Daily Dose Reminder

```yaml
alias: "Morning Medication Reminder"
trigger:
  - platform: time
    at: "08:00:00"
condition:
  - condition: numeric_state
    entity_id: sensor.metformin_500mg_doses_today
    below: 1
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "💊 Medication Reminder"
      message: "Don't forget your morning Metformin 500mg."
```

> Blueprint files for common automation patterns will be available in the [`/blueprints`](./blueprints) directory.

---

## 🖥️ Lovelace Dashboard Cards

A sample dashboard configuration is provided in [`/lovelace`](./lovelace/example-dashboard.yaml).

**Recommended cards:**

- [**button-card**](https://github.com/custom-cards/button-card) — Quick-log dose buttons
- [**mushroom-cards**](https://github.com/piitaya/lovelace-mushroom) — Clean medication status chips
- [**mini-graph-card**](https://github.com/kalkih/mini-graph-card) — Dose history over time
- [**stack-in-card**](https://github.com/custom-cards/stack-in-card) — Grouped medication panels

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome and encouraged!

1. **Fork** this repository.
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes with a clear message (see [Commit Guidelines](#commit-guidelines) below).
4. Push to your branch: `git push origin feature/your-feature-name`
5. Open a **Pull Request** with a description of what you changed and why.

### Commit Guidelines

This project uses conventional commit messages for clarity and automated changelog generation:

| Prefix | Use for |
|---|---|
| `feat:` | New features |
| `fix:` | Bug fixes |
| `docs:` | Documentation changes |
| `style:` | Formatting, no logic change |
| `refactor:` | Code restructuring |
| `test:` | Adding or fixing tests |
| `chore:` | Maintenance, dependencies |

**Example:**
```
feat: add photo upload support to medication add form
fix: correct quantity sensor state reset on HA restart
docs: update README with Lovelace example dashboard
```

### Development Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/medication-tracker.git
cd medication-tracker

# Set up a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements_dev.txt

# Run tests
pytest tests/
```

A full development environment guide is available in [`CONTRIBUTING.md`](./CONTRIBUTING.md).

---

## 📄 Changelog

See [CHANGELOG.md](./CHANGELOG.md) for a full history of releases, features, and fixes.

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

---

## ⚕️ Disclaimer

> **This integration is not a medical device and is not intended to replace professional medical advice, diagnosis, or treatment.** It is a personal convenience tool only. Always follow the guidance of your healthcare provider regarding medications, dosages, and schedules. The authors accept no liability for missed doses, incorrect dosing, or any health outcomes related to the use of this software.

---

## 🙏 Acknowledgements

- Forked from [Item-Tracker](https://github.com/yourusername/item-tracker)
- Built on the [Home Assistant](https://www.home-assistant.io/) platform
- Inspired by the HA community's dedication to local-first, privacy-respecting home automation

---

<p align="center">Made with ❤️ for the Home Assistant community</p>
