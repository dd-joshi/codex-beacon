# Solo-maker premium Lite/Pro plan

**Decision date:** 14 August 2026  
**Status:** Current authoritative execution plan  
**Founder reality:** One employed electronics engineer in India, using only genuinely personal time, equipment, accounts, and money  
**Business objective:** Create disciplined side income without risking the job or pretending to be a funded consumer-electronics company

> **Architecture amendment — 14 August 2026:** Technical implementation is governed by the [local Wi-Fi software prototype plan](software-prototype-plan.md). The current executable scope ends at its software-prototype gate. Paid or delivered hardware remains on Hold until the excluded power subsystem has a separately approved scope and safety/readiness evidence outside this repository.

## The corrected product thesis

Peri6 remains a premium six-cell desktop status instrument. It is not reduced to one permanent Blender gadget, but it will grow through trustworthy category packs rather than launching five unreliable features at once.

The commercial structure is:

- one shared physical product;
- one stable, application-agnostic ESP firmware and one upgradeable Windows desktop host;
- five modular category packs;
- two paid software/service entitlements: Lite and Pro;
- handmade, build-to-order batches until demand and quality justify anything larger.

The founder's salary limits personal cash exposure. It does not force the selling price to be cheap.

## Gate Zero — employment and ownership

Before public development or spending:

- review the appointment letter, employee handbook, moonlighting/outside-business rules, confidentiality terms, and invention/IP assignment;
- use no employer-paid duty time unless written permission explicitly allows the activity;
- use only a personal computer, phone, internet connection, repository, software licences, tools, parts, suppliers, and workspace;
- expose no employer code, design, lab, badge, screen, document, vendor information, customer information, or confidential method;
- keep dated personal commits, receipts, design notes, and build records.

If ownership or conflict is unclear—especially if the employer works in electronics, embedded systems, desktop software, LEDs, or adjacent products—pause and obtain qualified advice or written clearance. Preserving a ₹35,000 monthly job is more important than accelerating a speculative side product.

## One shared hardware platform

Lite and Pro must not become two PCBs, component lists, cartons, repair pools, or firmware images.

Both use:

- six optically isolated addressable-light cells;
- an ESP connected locally to the same private home router as the Windows companion;
- one button;
- ambient-light sensing if it survives the cost/reliability test;
- the same enclosure, finish, serial process, test procedure, and pack-agnostic firmware;
- local/account-free operation with no required internet, cloud, subscription, or router port-forward.

Use the available ESP development board for the software prototype. USB may be used for flashing, logs, and recovery, but not as the normal product data path. No custom PCB, tooling, or inventory batch is allowed before at least 20 paid deliveries and approximately ₹50,000 cumulative contribution.

Battery selection, charging, protection, conversion, runtime estimation, indication, sleep strategy, and power optimization are outside this repository and current gate. The software assumes a powered, awake ESP; no commercial hardware commitment may treat that excluded subsystem as complete.

Exactly one application pack is active at a time. Internally, that pack produces a common event conceptually:

`category + state + confidence + optional progress + expiry + explanation`

The active pack owns its application adapter, state interpretation, explanation, and distinctive visual recipe. The desktop host owns activation, rejects late events from the previous pack, applies shared brightness/accessibility limits, and compiles the recipe into a generic scene/keyframe command. The ESP sees no category, application, state, or entitlement meaning; it only validates and renders the scene and expires it when stale. A pack or desktop release can therefore improve without changing compatible ESP firmware.

## Five category packs

| Category | First honest scope | Customer value | Release order |
|---|---|---|---:|
| Focus | Local countdown, button/tray start, quiet completion marker | Daily use even when no task integration is active | Core/0 |
| Creator | Blender render started, working, completed, cancelled/failed; later apps only when verified | Walk away from long renders | 1 |
| Stream/Recording | OBS streaming/recording active, stopped, and error through OBS's authenticated local WebSocket, separate from the Peri6 device session | Know whether recording/stream state is safe | 2 candidate |
| Developer | Explicit command wrapper using real command exit status; no guessed IDE success | Walk away from builds, tests, backups, and scripts | 2 candidate |
| System Health | Sustained CPU, memory, disk-pressure, connectivity, and only verified temperature sources | Calm reassurance without a sensor dashboard | Last |

[Blender exposes render initialization, completion, and cancellation handlers](https://docs.blender.org/api/current/genindex-R.html), making it a bounded first Creator integration. [OBS includes WebSocket support from version 28](https://obsproject.com/kb/remote-control-guide); authentication remains mandatory.

After Creator, paid pack selections decide whether OBS or Developer is next. System Health comes last because hardware-dependent data is noisy and claims are easy to overstate.

## Published versus roadmap packs

A category may appear in engineering content as a prototype, but it becomes **Published** only when:

- exact supported workflow/application versions are named;
- start, working, completed, failed/cancelled, disconnected, stale, and unknown behavior are tested where applicable;
- no tested failed/cancelled outcome appears as successful;
- setup and removal instructions exist;
- install, activate, deactivate, update, and removal behavior passes on every supported desktop-host version without requiring a compatible ESP firmware change;
- stopping or switching away from the pack cannot publish a late scene;
- unsupported cases fail honestly;
- at least three external users complete a two-week pilot for the maker batch;
- the founder can support it within the available weekly time.

Only Published packs appear as included purchase features. “Coming soon” is a roadmap statement, never part of a paid entitlement.

## Lite and Pro offers

Both are premium and use identical hardware. Pro charges for breadth and automation—not better safety, reliability, firmware recovery, warranty handling, or basic build quality.

| Capability | Peri6 Lite | Peri6 Pro |
|---|---|---|
| Customer price hypothesis | **₹6,999** | **₹9,999** |
| Hardware/build quality | Identical six-cell premium maker unit | Identical six-cell premium maker unit |
| Focus | One countdown, quiet hours, completion marker | Saved schedules/presets and activation shortcuts |
| Category packs | Choice of one Published pack | All Published packs available at purchase |
| Active packs | Exactly one at a time | Exactly one at a time; Pro provides a broader selectable pack library, not simultaneous monitoring |
| Completion memory | Most recent completion | Small local completion queue/history |
| Explanation | Current state and source | Current state, reason, and optional seven-day local history |
| Rules | Curated safe defaults | User thresholds, pack presets, activation automation, quiet schedules |
| Automation | Selected pack only | Local CLI and authenticated localhost webhook after verification |
| Support | Written setup and the same safety/warranty path | Same support SLA; no unsustainable phone/WhatsApp promise |
| Upgrade | Lite-to-Pro local entitlement: **₹3,499** | — |

Additional Published category pack for Lite: **₹999**.

The entitlement is a signed local desktop configuration tied to the device serial. No account, cloud check, different hardware, or different firmware image is required. A Lite unit upgrades digitally without replacement; the ESP still does not know which pack or tier is active.

Do not accept full Pro payment until at least two useful Published packs exist. A refundable Pro reservation may be used to measure demand when the exact current and required shipment capabilities are disclosed.

## Price and cost discipline

Treat ₹6,999/₹9,999 as hypotheses to test, not as established value. Use a ₹699 refundable Lite reservation and ₹999 refundable Pro reservation, credited to the final purchase. Show the full price, current Published packs, shipping treatment, estimated delivery, handmade-pilot status, support limits, and refund terms before payment.

Planning cost targets:

- finished assembled/tested/packed unit: preferably no more than ₹2,300;
- absolute landed unit ceiling: ₹2,500;
- hands-on build and end-of-line test: no more than three hours initially, moving toward 90 minutes;
- reserve customer money until the promised unit can be delivered or refunded;
- no cash-on-delivery during the pilot; standard prepaid India shipping may be included in the displayed test price.

These commercial figures do not estimate or authorize the excluded power subsystem. They cannot support a paid-unit decision until a separate complete-unit cost and safety/readiness input is approved.

Until a chartered accountant confirms actual classification and obligations, model an 18% tax reserve rather than treating the full customer payment as spendable cash. This is a conservative planning assumption, not tax advice.

| Planning metric | Lite | Pro |
|---|---:|---:|
| Customer price | ₹6,999 | ₹9,999 |
| Approximate revenue after 18% planning reserve | ₹5,931 | ₹8,474 |
| Target assembled/tested/packed cost | ₹2,300 | ₹2,300 |
| Payment, standard shipping, support, and warranty allowances | Approximately ₹890 | Approximately ₹1,160 |
| Target contribution before advertising and founder income tax | **Approximately ₹2,700** | **Approximately ₹5,000** |

If the finished unit cannot look and behave premium at these prices, improve the actual product or stop. Do not use cinematic content to disguise a rough prototype.

## Ninety-day product and sales plan

Plan only 8–12 genuinely personal product hours per week. Content receives a separate maximum of three hours per week under the [Instagram plan](../04-commercial/instagram-build-in-public-plan.md).

### Days 1–7 — permission and clean separation

- Record Gate Zero as Passed.
- Create personal project accounts/repository and a cash/time ledger.
- Freeze the pack-host API, local-LAN scene protocol, and actual ESP pin map.
- Record that the available desk hardware is sufficient; order nothing unless a missing prototype part is identified.

**Cash ceiling:** ₹3,000.  
**Stop:** unclear employer ownership or conflict.

### Days 8–21 — one premium-direction prototype

- Build one shared hardware prototype; no Lite/Pro electronics split.
- Build the generic ESP keyframe renderer and authenticated same-router connection.
- Build the upgradeable desktop host with an atomic single-active-pack lifecycle.
- Make the Focus pack exercise every core scene primitive and physical control.
- Implement the bounded Blender Creator pack and its own visual recipes without changing firmware.
- Produce two enclosure/diffuser iterations only if the first cannot support the premium claim.
- Record real build/test footage as a by-product.

**Pass:** exactly one active pack; a dummy new pack works without host-core or firmware edits; honest Working, Done, Failed/Cancelled, Unknown, disconnect and acknowledge behavior; authenticated local control; stale-scene expiry; router/desktop/ESP reconnect; usable across-room optics. This pass makes no battery or power-system claim.

### Days 22–30 — offer before breadth

**Entry condition:** the software-prototype gate has passed and every excluded hardware dependency required for a paid unit has separately approved readiness evidence. Until then this phase is on Hold.

- Publish one genuine 15–30 second hero demonstration.
- Publish one exact Lite/Pro comparison page with real current capabilities.
- Offer no more than five founder-batch slots.
- Collect only reviewed refundable reservations.
- Drive qualified visitors from Instagram and relevant creator/developer communities; do not run paid ads.

**Micro-demand gate:**

- at least 100 qualified landing visits;
- at least five unrelated paid reservations;
- at least two Pro selections;
- at least three people explicitly accept the displayed full price;
- personal validation spend remains at or below ₹5,000.

Zero or one reservation means the offer is not proven. Do not respond by adding four unfinished packs.

### Days 31–60 — five identical physical units

- Buy parts only for paid/reserved units.
- Build no more than five shared-hardware units.
- Publish Creator and Focus only if they pass; develop OBS or Developer next according to paid selection evidence.
- Run and record the same end-of-line test for every serial: private-LAN join, discovery/manual fallback, pairing/authentication, capability handshake, every cell, button/sensor, scene expiry, reconnect, success/failure cycles, and soak. Power-system evidence remains a separate prerequisite outside this repository.
- Deliver current functionality honestly; do not bill roadmap features as completed.

**Five-user gate:**

- at least four activate with no more than 30 minutes of help;
- at least three use a primary pack weekly after 30 days;
- zero tested failed/cancelled tasks displayed as Done;
- no safety/thermal incident;
- support remains below two hours per customer in month one;
- no more than one return.

### Days 61–90 — prove breadth without multiplying hardware

- Release the next paid-priority category only after its pack gate.
- Improve the common enclosure, assembly/test repeatability, documentation, and updater/recovery—not the feature count for its own sake.
- Open a second five-unit build-to-order batch only after the first-user gate passes.
- Publish real deposits, hours, failures, active use, refunds, and contribution without revealing customer or employer data.

**Day-90 continuation gate:**

- at least 10 unrelated paid reservations or purchases;
- at least five delivered units and three retained weekly users;
- at least two organic/referral orders;
- unit contribution and founder time remain viable;
- Instagram contributes at least one customer or is deliberately demoted as a channel;
- no employment/IP, safety, refund, or cash problem.

## When two tiers or hardware changes become real

The first five reservations only justify a maker batch. They do not validate long-term price segmentation.

Keep Lite/Pro only after at least 30 paid reservations or 20 paid deliveries when:

- at least 20% and no more than 70% choose Pro;
- Pro users actually use two or more packs;
- users understand that those packs are selected one at a time rather than monitored concurrently;
- Lite users remain satisfied rather than feeling artificially restricted;
- the upgrade and entitlement system creates less support than the added margin.

If Pro take rate is below 20%, sell one product plus à-la-carte packs. If it exceeds 70%, test one complete bundle. Do not create a second physical SKU until several hundred units and stable demand make separate inventory rational.

## Claims that remain forbidden

- works with every renderer, IDE, GPU, streaming tool, or Windows PC;
- always shows exact progress;
- automatically understands success from every ordinary process;
- prevents overheating, crashes, lost renders, or failed recordings;
- zero setup, zero false alerts, or lifetime compatibility;
- unpublished category packs included in a paid purchase;
- macOS, Linux, cloud, mobile, off-LAN control, remote notification, or simultaneous multi-pack monitoring in the current offer;
- production certification or mass-production durability for handmade pilots;
- custom integrations included with Pro;
- unlimited personal support or all future packs forever.

Unknown remains an honest state. A failed task is never allowed to look successful.

## Realistic side-income interpretation

At the planning contribution targets, roughly two Lite sales and one Pro sale in a month could produce around ₹10,000 contribution before founder income tax and unplanned costs. That is a possible small-volume outcome, not a forecast. The first objective remains one excellent prototype, five paid reservations, and five trustworthy deliveries—not followers, market share, or leaving the job.
