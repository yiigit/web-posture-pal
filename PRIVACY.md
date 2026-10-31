# Privacy and compliance scope

PosturePal provides privacy safeguards; this repository is not a GDPR/HIPAA compliance certification or a ready-to-use regulated healthcare deployment.

## Daily activity flow

- Guests: only the current local day's habit identifiers and completed-break count are stored in `posturepal.daily` in that browser. The server is contacted to check sign-in status, but receives no guest activity. A failed status check pauses recording rather than assuming guest status.
- Signed in: activity is saved against the authenticated account, not browser localStorage. The API accepts the local calendar date, an allowed habit identifier/completed flag, or a random break-event UUID. It does not receive exercise category, pain notes, location, images or camera data.
- No automatic migration: signing in never imports the device's existing guest history. Signing out clears account activity from UI state and restores only separately recorded guest data. An expired session or failed save never writes account data to guest storage.
- Account switching: mutation requests bind to the expected signed-in identity; stale tabs cannot silently record against another user's session. Breaks started under another identity are not reassigned.
- Private by default: friends, bootstrap administrator tokens, and social statistics have no activity-history access. Publishing a social update remains a separate, explicit action.
- Persistence: MySQL stores daily aggregates and random event identifiers for idempotency; no activity payloads are logged. Private activity paths are excluded from Uvicorn access logs to avoid logging habit IDs/dates; operators must also configure upstream proxies and infrastructure logs appropriately. Dates follow the browser's local calendar; the account time-zone preference does not reassign existing days.
- Favorites are still browser-local, independent of account daily activity.

## Derived achievements and live updates

Badges, trophies, points and progress grids are derived from the same retained daily aggregates. No separate permanent achievement history, personal ranking or new activity telemetry is stored. Clearing activity removes its derived achievements; retention expiry and unchecked habits can also change progress. Guests receive today-only badges computed in the browser. Signed-in endpoints enforce the same owner/session identity checks as daily activity.

Visible signed-in pages poll activity/progress every 15 seconds. Hidden tabs pause polling. Refresh payloads are never written into guest storage or shared socially. Motivational messages contain no diagnosis or medical prediction. Extra breaks beyond three per day do not add points, reducing incentives to chase excessive activity.

## User controls

`/account.html` includes an activity privacy panel. Signed-in users can download retained daily activity as JSON or delete it from the active database. Guests can export/delete this browser's current daily activity. Export is scoped to daily activity, not a comprehensive subject-access export of profiles/social records.

Account deletion removes daily aggregates/events through foreign-key cascades, along with existing profile/session/social deletion behavior. Deleting daily activity alone does not remove independently published social posts; those have their own delete/visibility controls.

## Retention

Daily account records use a rolling 90-day UTC cutoff (with one day of forward date allowance for browser time zones). Expired dates are inaccessible immediately; physical cleanup runs at startup and hourly while the API runs. Operators can also schedule:

```bash
python -m posturepal.commands.purge_activity
```

Cleanup failures log a generic operational message and retry the next hour. Operators must monitor failures and implement a backup retention/deletion policy. Backups, replicas, access logs and downloaded exports are outside the active-database deletion guarantee. Guest records are discarded on the next local day when the app is opened or running.

## Technical safeguards included

Authenticated own-account endpoints, strict request schemas, expected-user verification, CSRF request verification, no-store API responses, session revocation, least-data daily aggregates, idempotent break events, account-deletion cascades, private social audiences and no automatic analytics/third-party font requests. The automated suite checks isolation, unauthenticated writes, retention, erasure and account-switch handling.

## Deployment responsibilities and remaining gaps

Before collecting regulated personal/health information, the operator must establish and document:

- Identity/contact details of the controller, legal basis and purpose of processing, notices, consent/withdrawal where applicable, processor agreements and international-transfer safeguards.
- Procedures for access, correction, erasure, restriction, objection and portability requests across all stores (including profile/social information), plus backup handling and breach response.
- HTTPS with secure cookies, restricted database/network access, encryption at rest and for backups, key management, least-privilege operator access, monitoring and appropriate audit trails. This code does not itself enable database encryption or supply a complete tamper-evident audit system.
- Applicable risk assessments/DPIAs, security assessments, staff policies/training, incident response, business continuity and retention schedules appropriate to the deployment.
- Whether HIPAA applies, based on covered-entity/business-associate status; if applicable, appropriate BAAs and administrative, physical and technical safeguards. No HIPAA suitability assessment or BAA is provided by this project.

Do not describe the app as “GDPR compliant” or “HIPAA compliant” solely because these features exist. Medical/health information should not be put into profiles or social posts before the operator has completed the applicable assessment.

Authoritative references:

- [European Commission: GDPR principles](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/principles-gdpr_en)
- [European Commission: individual rights](https://commission.europa.eu/law/law-topic/data-protection/information-individuals_en)
- [HHS: HIPAA covered entities and business associates](https://www.hhs.gov/hipaa/for-professionals/covered-entities/index.html)
- [HHS: HIPAA Security Rule summary](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html)


## Optional external AI coach

AI chat is disabled unless an operator configures a server API key and model. Signed-in users must explicitly consent before sending messages, and may inspect the exact context on the chat page. Each send transfers to OpenAI the message/current in-memory conversation, display name, time zone, activity totals from the retained 90-day window, derived points/level/awards and seven days of daily activity counts. Email addresses, bios, friends, passwords, session secrets and browser-local guest activity are not included. Users should avoid typing sensitive medical or identifying information into messages.

The app stores no conversation transcript or consent record on disk, in its database, or in browser storage. Consent applies to the current page conversation and resets on clearing or a detected account change. Refresh/navigation discards the transcript. The provider request uses `store: false` and no server-side conversation ID, but provider processing/logging and contractual retention can still apply. Local deletion or clearing chat cannot retract an already submitted request or delete provider logs. Operators must explain provider policies and rights processes in their own notice; code alone does not establish GDPR/HIPAA compliance or an appropriate legal basis/BAA.

AI answers cannot modify activity, profile or social records. Context is read from the authenticated account and bound to the expected account ID, not client-supplied statistics. CSRF verification and per-account throttling apply. Hashed request counters expire after 15 minutes and are cleaned by the existing throttle mechanism; they contain no messages/activity. Chat request paths are excluded from Uvicorn access logs. Upstream errors are sanitized; reverse proxies/APM must separately avoid capturing request bodies. Conversation data is present in process memory during requests and can remain in browser memory until clearing/navigation or session-change detection. A request already sent can continue processing even after browser cancellation.
