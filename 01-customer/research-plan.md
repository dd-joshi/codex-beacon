# Customer research plan

> **Status:** Future scaled research reference. The current solo-maker experiment uses paid offer behavior and five-unit field evidence defined in the [Lite/Pro plan](../03-roadmap/solo-maker-lite-pro-plan.md); current technical evidence follows the [software prototype plan](../03-roadmap/software-prototype-plan.md).

## Research objective

Determine whether Peri6 solves a recurring, valuable problem strongly enough to justify custom hardware.

The research must answer:

1. Who most often waits on long computer tasks?
2. What do they do today, and what does that cost them in attention or time?
3. Is a calm physical signal genuinely better than existing notifications for this job?
4. Which selectable pack—Creator/Task, Health, or Focus—creates repeated use after novelty fades when exactly one is active at a time?
5. Can six cells communicate reliably without becoming distracting?
6. Will qualified users commit money near viable pricing?

Do not ask whether “an LED dashboard sounds cool.” Study recent behavior and require evidence through use and payment.

## Target cohorts

Gate G1 uses one commercial cohort, reported separately from comparison research:

| Cohort | Target | Qualification | Counts toward US demand gate? |
|---|---:|---|---|
| US video editors, motion designers, and 3D artists | 20 interviews; 10–15 desk trials | Windows; dedicated workstation; at least three renders/exports per week lasting at least 15 minutes | Yes |
| Indian video/3D/motion creators | 5 interviews; later 10–20 beta users if useful | Same workflow screen | No; workflow/usability comparison only |
| Accessibility-focused participants | Included across the US cohort and supplemented where necessary | Color-vision, low-vision, motion/photosensitivity, or motor-access needs | Yes when they meet the commercial screen |

Developers and streamers are secondary segments. Study them only after the initial cohort is decided; do not blend them into G1 results. Avoid over-recruiting desk-gadget enthusiasts because they can overstate decorative appeal.

## Screening requirements

Participants should:

- perform the relevant workflow themselves;
- describe a concrete occurrence from the previous two weeks;
- work at a PC several days per week;
- be able to use a test device or simulation in their real environment;
- not be employed by the product team or close friends/family for gate evidence.

Capture workstation type, OS, GPU/CPU, applications, task duration, room/desk layout, viewing distance, existing notifications, and willingness to install a lightweight local utility.

## Research sequence

### R1 — Problem interviews and observation, weeks 1–2

Conduct 20 qualified US sessions and five separately reported Indian comparison sessions. Observe actual workflow when possible.

Ask for recent stories:

- “Tell me about the last long task you waited for.”
- “What did you do after pressing Start/Export/Build?”
- “How did you know it was still working?”
- “What happened when it failed or took longer than expected?”
- “How often did you return to check?”
- “What notification or remote method did you use?”
- “When would a light be worse than the current method?”

Measure behavior, frequency, consequence, workaround, trust, privacy concern, and purchasing context.

Avoid leading questions, feature lists, or asking participants to predict future daily use.

### R2 — Diary study, weeks 2–4

Select 10–12 strong participants for a two-week diary.

For every relevant task, record:

- application and task type;
- expected and actual duration;
- whether the user stayed, left, or repeatedly checked;
- number of checks;
- failure, cancellation, stall, or completion;
- notification used;
- emotional consequence and lost time;
- whether a calm persistent completion marker would have helped.

The diary determines frequency and reveals workflows worth supporting first.

### R3 — Visual-language comprehension, weeks 2–5

Test simulated or rough physical patterns before explaining them, then after a one-minute introduction.

Include:

- calm;
- working with unknown percentage;
- exact progress;
- attention;
- urgent;
- successful completion;
- failed/cancelled task;
- unavailable sensor/device disconnected;
- focus timer.

Test at desk distance and across-room distance, in day/night conditions, with reduced motion and color removed. Record interpretation, confidence, response time, confusion, and distraction.

### R4 — Concierge desk trial, weeks 3–6

Place 15 rough devices or high-fidelity simulations in real workspaces for at least two weeks.

The trial may use manual or limited integrations; the goal is behavior, not scalable engineering.

Track:

- tasks watched per week;
- whether the participant walks away;
- completion markers noticed;
- unnecessary attention events;
- dim/mute/disable/power-off behavior;
- requests for explanation;
- false success and false urgent events;
- which selected pack creates repeat use across sessions;
- placement and preferred viewing distance.

At the end, remove the product for several days and ask what changed. Missing the behavior is stronger evidence than liking the prototype.

### R5 — Positioning and price, weeks 4–7

Test three lead messages separately:

1. “Know when your work is finished.”
2. “Your computer has body language.”
3. “The physical status bar your computer forgot.”

Evaluate 15-second comprehension, benefit recall, “just RGB” interpretation, and qualified conversion.

Use structured price testing across $99–$129, followed by a legally and operationally reviewed refundable USD $10 reservation. Aim for at least 500 qualified US visits; report waitlist signups separately because they are not purchase evidence.

## Evidence capture

For each study, preserve:

- research question and pre-agreed threshold;
- recruiting criteria and participant IDs;
- protocol and stimulus version;
- raw notes/recordings with consent;
- observed behavior and direct statements kept distinct;
- numerator/denominator for every rate;
- dropouts and missing data;
- segment and accessibility differences;
- synthesis, contradictions, and recommended decision.

Use the [experiment card](../templates/experiment-card-template.md) for every material test.

## Privacy and participant care

- Collect the minimum information needed.
- Do not capture private file names, client media, source code, or process names without explicit need and consent.
- Redact recordings and diagnostic exports.
- Explain what the prototype observes and whether any operator manually controls it.
- Provide an immediate lights-off and withdrawal option.
- Compensate participants consistently.
- Separate research consent from marketing/testimonial permission.

## Research outputs

By Gate G1, the team produces:

1. Ranked jobs-to-be-done and segment evidence
2. Current journey and workaround map
3. Hero journey and top failure expectations
4. Validated/rejected visual patterns
5. Accessibility findings
6. First supported workflow shortlist
7. Positioning and paid price evidence
8. Repeat-use and removal-test evidence
9. Product requirements and explicit non-requirements
10. Go, Conditional Go, Hold, or Stop/Pivot recommendation

## Gate G1 minimums

The complete thresholds are in the [validation scorecard](validation-scorecard.md). The core minimums are:

- recurring weekly problem in the chosen segment;
- fast comprehension of calm, working, done, and attention;
- repeated watched-task behavior during real use;
- strong “very disappointed if removed” evidence;
- credible refundable reservations near viable pricing;
- value described as reassurance/freedom, not only decoration.

If these do not pass, do not rationalize the result with more features. Narrow, pivot, or stop before custom tooling.
