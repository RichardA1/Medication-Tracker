# 🖥️ Medication Tracker — Lovelace Dashboards

This directory contains ready-to-use Lovelace dashboard configurations for the
[Medication Tracker](../README.md) Home Assistant integration.

---

## 📋 Available Dashboards

| File | Cards Required | Description |
|------|---------------|-------------|
| [`example-dashboard.yaml`](example-dashboard.yaml) | Built-in only | Universal — works without any HACS cards |
| [`mushroom-dashboard.yaml`](mushroom-dashboard.yaml) | HACS custom cards | Premium look with Mushroom + button-card |

---

## 🔧 Quick Start

### Step 1 — Install the Medication Tracker integration

Follow the [main README](../README.md) installation instructions first.
You must have at least one medication added before the dashboard is useful.

### Step 2 — Find your entity IDs and item UUIDs

**Entity IDs** (used in card configuration):

1. Go to **Developer Tools → States**
2. Filter by `medication_tracker` or your medication name
3. Note the full entity ID, e.g. `sensor.metformin_500mg`

**Item UUIDs** (used in service call `service_data`):

1. Go to **Developer Tools → States**
2. Click on a medication sensor entity
3. Expand the **Attributes** section
4. Copy the `item_id` value — it is a UUID like `a1b2c3d4-e5f6-...`

### Step 3 — Choose a dashboard file

- **No HACS?** → Use `example-dashboard.yaml`
- **Have HACS + custom cards?** → Use `mushroom-dashboard.yaml` for the best experience

### Step 4 — Edit the placeholder values

Open the YAML file and replace every placeholder:

| Placeholder | Replace with |
|-------------|-------------|
| `sensor.YOUR_MEDICATION_ENTITY_1` | Your first medication's entity ID |
| `sensor.YOUR_MEDICATION_ENTITY_2` | Your second medication's entity ID |
| `YOUR_ITEM_UUID_1` | `item_id` attribute from the first sensor |
| `YOUR_ITEM_UUID_2` | `item_id` attribute from the second sensor |
| `YOUR_HA_USERNAME` | Your HA username (for the Actions view restriction) |

Add or remove medication blocks as needed — each one follows the same
repeating pattern and is clearly marked in the file with comments.

### Step 5 — Add the dashboard to Home Assistant

**Option A — New sidebar dashboard (recommended):**

1. Go to **Settings → Dashboards**
2. Click **+ Add Dashboard**
3. Choose **Empty dashboard**, give it a title (e.g. "Medications")
4. Click the three-dot menu → **Edit Dashboard** → **Raw configuration editor**
5. Paste the contents of your chosen YAML file and click **Save**

**Option B — Import as a view into your existing dashboard:**

1. Open your existing dashboard's raw configuration editor
2. Copy one or more `views:` entries from the YAML and paste them into your
   existing `views:` list

**Option C — Full YAML mode (advanced):**

```yaml
# configuration.yaml
lovelace:
  mode: yaml

# ui-lovelace.yaml or referenced dashboard file — include the views block
```

---

## 📦 Required Custom Cards (mushroom-dashboard.yaml only)

Install all of these via **HACS → Frontend** before using the Mushroom dashboard:

| Card | HACS Name | Repository |
|------|-----------|-----------|
| Mushroom | `Mushroom` | [piitaya/lovelace-mushroom](https://github.com/piitaya/lovelace-mushroom) |
| Button Card | `button-card` | [custom-cards/button-card](https://github.com/custom-cards/button-card) |
| Stack in Card | `stack-in-card` | [custom-cards/stack-in-card](https://github.com/custom-cards/stack-in-card) |
| Card Mod | `card-mod` | [thomasloven/lovelace-card-mod](https://github.com/thomasloven/lovelace-card-mod) |
| Auto Entities | `auto-entities` | [thomasloven/lovelace-auto-entities](https://github.com/thomasloven/lovelace-auto-entities) |

After installing each card in HACS, **restart Home Assistant** and then
**clear your browser cache** before loading the dashboard.

---

## 🗂️ Dashboard Views

### Overview
- Quick summary of all medications with quantity and low-stock status
- Today's scheduled doses at a glance
- Low-stock alert banner (only appears when needed)
- Navigation buttons to Medications and Schedules views
- Link to the integration config flow to add/edit medications

### Medications
- Full detail card for each medication including:
  - Photo (if configured via `photo_path`)
  - Name, dosage, instructions
  - Quantity on hand with refill threshold
  - Next scheduled dose time
  - Full schedule table (days, time, dose amount, enabled status)
  - **Take Dose** button — deducts one dose from stock (with confirmation)
  - **Add Stock** button — adds your refill quantity (with confirmation)
  - **Manage** button — opens the integration config flow

### Schedules
- Full week grid showing every medication's scheduled dose times
- Today's doses highlighted with individual **Take** buttons per medication
- Only shows medications that have a dose scheduled for the current day

### Actions *(example-dashboard.yaml only)*
- Manual service call panel for power users
- Input fields for Item ID and quantity/dose amount
- Buttons to call `take_dose`, `add_quantity`, and `set_quantity` services directly
- Requires adding helper entities — see the YAML for the `configuration.yaml` snippet

---

## 🎨 Customisation Tips

### Changing the refill quantity on the "Add Stock" button

Each **Add Stock** button has a hardcoded `quantity` in its `service_data`.
Change this to match your typical prescription fill size:

```yaml
tap_action:
  action: call-service
  service: medication_tracker.add_quantity
  service_data:
    item_id: YOUR_ITEM_UUID_1
    quantity: 90    # ← change to 90 for a 90-day supply, etc.
```

### Changing the dose quantity on the "Take Dose" button

If a medication's scheduled `dose_quantity` is not 1 (e.g. take 2 tablets),
update the button to match:

```yaml
service_data:
  item_id: YOUR_ITEM_UUID_1
  dose_quantity: 2    # ← match your schedule's dose_quantity
```

### Dynamic refill using an input_number

For a more flexible Add Stock button, use an `input_number` helper:

```yaml
# configuration.yaml
input_number:
  metformin_refill_qty:
    name: Metformin Refill Quantity
    min: 1
    max: 365
    step: 1
    initial: 90
```

Then reference it in the service call:

```yaml
service_data:
  item_id: YOUR_ITEM_UUID_1
  quantity: "{{ states('input_number.metformin_refill_qty') | float }}"
```

### Adding a medication photo

In the integration config flow, set the **Photo Path** field to a path
served by HA's media server, e.g.:

```
/media/local/medications/metformin.jpg
```

Upload the photo to `config/www/medications/metformin.jpg`, then reference
it as `/local/medications/metformin.jpg`.

The `picture-entity` and `mushroom-template-card` in the dashboard will
automatically display it as the card image.

---

## 🤖 Combining with the Automation Blueprint

The [medication_reminder.yaml](../blueprints/automation/medication_tracker/medication_reminder.yaml)
blueprint handles automated TTS reminders and dose logging. The dashboard
complements it — the blueprint logs doses automatically via automation while
the dashboard provides manual **Take Dose** buttons as a fallback.

If you enable **Auto-Log Dose** in the blueprint, avoid also pressing the
**Take Dose** button for the same dose to prevent double-counting.

---

## 🛠️ Troubleshooting

**Cards show "Entity not found" or are blank.**
- Confirm the entity IDs are correct: **Developer Tools → States**
- Make sure at least one medication has been added via the integration config flow

**"Take Dose" button does nothing.**
- Check the `item_id` UUID — it must exactly match the `item_id` attribute
  on the sensor (copy-paste from Developer Tools, don't retype)
- Check **Settings → System → Logs** filtered by `medication_tracker` for errors

**Photos are not showing.**
- The path must be accessible to the HA frontend: store images in `config/www/`
  and reference them as `/local/...`
- Ensure the `image` field in the `picture-entity` card resolves to a non-empty
  value; the dashboard falls back to the HA favicon if `photo_path` is empty

**Schedule table is empty.**
- Add schedules via **Settings → Integrations → Medication Tracker → Configure
  → Add a dose schedule**
- After adding, reload the dashboard (Ctrl+Shift+R)

**Mushroom cards not rendering.**
- Verify all required HACS cards are installed and HA has been restarted
- Clear your browser cache (Ctrl+Shift+Delete) after installing new frontend resources

---

## 🤝 Contributing

Dashboard improvements and new card examples are welcome! Please open a pull
request in the main repository. See [CONTRIBUTING.md](../CONTRIBUTING.md).

---

<p align="center">Part of the <a href="../README.md">Medication Tracker</a> project for Home Assistant</p>
