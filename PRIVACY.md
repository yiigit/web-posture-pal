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
