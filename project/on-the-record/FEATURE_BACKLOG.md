# Feature backlog — On the Record

Recorded: 16 October 2026. Status updated: implemented locally; email delivery and real-device acceptance remain gated as detailed below.

## Implementation status — 16 October 2026

- F1: canonical topic URLs, automatic SSR result, shared five-minute read-only result cache, metadata, dynamic 1200x630 PNG, social links, copy/native sharing and quote-card hand-off implemented. Real topic page/HEAD and OG PNG return 200, required metadata exists; PNG visually checked. Preview uses the existing verified timeline pipeline, retaining only its first item for metadata/image; retrieval itself is unchanged. A URL reproduces a query, not an immutable snapshot. Public sharing requires a public deployment and SITE_URL.
- F5 then F3: pure email/petition formatters, shared accessible modal, clipboard, official contact lookup, mailto fallback and change.org hand-off implemented. Six template tests pass. Two real OpenAustralia member lookups returned no email fields; null plus parliamentary contact link is intentional. No email/petition submitted.
- F4: device share sheet, copy/mail fallback and explicit optional Contact Picker implemented. Contact data stays in the browser until passed to the user's chosen mail/SMS application; On the Record receives none. 390px layout and browser modal controls checked. Real iPhone/Android Contact Picker, external mail apps and Lighthouse have not been tested.
- F2: saved_quotes mapping, native source-checking/idempotent save_quote Workflow and tool, verified save API, browser capability ownership, saved list/delete UI and digest entry implemented. Live API test: save twice => one quote, mutation =>422, wrong capability =>403, delete succeeded. Final deletion also removes ownership/email, and refuses while delivery is pending. No login introduced; another browser cannot manage the collection without its local key. Email addresses are not URL parameters in the UI.
- Reminder delivery: complete native deterministic grouping/due/monthly/send/update Workflow registered valid but DISABLED. Six mock worker tests cover exact formatting, monthly gates, successful state updates, ambiguous-failure guard and stale-selection recheck. Read-only ES due query passed. Automatic approval review rejected a manual reminder execution because it could send email without explicit send authorization; no email was sent. EMAIL_CONNECTOR_ID and an authorized delivery test are still needed before enabling the schedule. No end-to-end email acceptance claim.
- General checks: thirteen frontend tests and three ingestion tests pass; production build and TypeScript checks pass (final integration rerun recorded in README). Desktop/390px UI checks performed; external social destinations were inspected, not posted to.

Implementation resolutions: incomplete coverage uses scoped absence wording throughout; original quotes are never shortened for mailto (copy full text if too long); templates retain the requested constituent statement with an edit reminder; share text includes attribution. Saved data management requires a browser-held random capability rather than email-only access. These are recorded behavior choices, not evidence that all original acceptance checks were performed.

This document consolidates the five feature requests supplied in chat. It is an implementation reference, not a verbatim transcript. The repeated attachment for saved quotes is counted once. Proposed resolutions below are separate from the requested requirements.

## Shared constraints

- Read README.md and the existing ui/ implementation before coding.
- Verified Hansard quotes only; preserve quote text byte-for-byte unless resolving an explicitly documented requirement conflict.
- Neutral factual wording; no editorialising.
- Attribution on every relevant surface: `Source: Parliament of Australia Hansard via OpenAustralia.`
- No analytics, tracking parameters, share-event logging, or logging of email bodies or contacts.
- ES_URL, ES_API_KEY and other secrets remain server-side.
- Reuse existing timeline, verification, toast, modal, and Workflow helpers.
- F1 must not change retrieval, agent instructions, or Workflows, and must not write to Elasticsearch. F2 explicitly requires new indices, Workflows, and agent tool registration within its own scope.

## F1 — Shareable finding URL, rich previews, and social sharing

### Context and outcome

Read `ui/app/speaker/[id]/page.tsx` and API routes. Existing speaker timeline uses POST /api/timeline, topics use GET /api/topics, and attention uses GET /api/attention. Share URLs should reproduce the finding for a speaker and topic.

### Requirements

1. Canonical URL: `/speaker/[id]?topic=<urlencoded>`. Automatically run the timeline when topic is present. Both searches and chips update the parameter through router.replace without a full reload.
2. Implement server-side generateMetadata in the speaker page. Fetch speaker name, party, electorate from members. With a topic, reuse the existing server-side timeline function to obtain the top verified quote; do not duplicate the ES query. Keep the quote lookup lightweight, size 1.
3. Title: `<Name> on <topic> — On the Record`; without topic: `<Name> — On the Record`.
4. Description: first verified quote truncated to 180 characters plus ` [<DD Mon YYYY>, <House|Senate>]`. Empty result: `No recorded statements on <topic> in Hansard since 1 Jan 2025.`
5. New `ui/app/api/og/route.tsx`, using next/og ImageResponse, 1200 × 630. Show speaker name, party, electorate, large quote, date/chamber, and full attribution at the bottom. Plain legible styling without party colours. Set `revalidate = 300`.
6. Set openGraph.images to the dynamic image and twitter.card to summary_large_image.
7. New `ui/components/ShareBar.tsx`, under a verified timeline or empty-state refusal only. Buttons: X, Facebook, WhatsApp, LinkedIn, Copy link, native Share, Download quote card.
8. Base share text: `What <Name> has said in Parliament on <topic> — verified Hansard quotes`. Completion criteria also require attribution in share text.
9. Social links open in a new tab with rel="noopener noreferrer":
   - X: `https://twitter.com/intent/tweet?text=<text>&url=<url>`
   - Facebook: `https://www.facebook.com/sharer/sharer.php?u=<url>`
   - WhatsApp: `https://wa.me/?text=<text>%20<url>`
   - LinkedIn: `https://www.linkedin.com/sharing/share-offsite/?url=<url>`
10. Native Share calls navigator.share({title, text, url}) when supported; otherwise hide it. Copy uses navigator.clipboard.writeText and the existing toast pattern for two seconds.
11. Instagram hand-off is Download quote card, opening `/api/og?speaker_id=...&topic=...` in a new tab; no Instagram intent URL.

### Required verification

- curl -I speaker URL returns 200. HTML contains og:title, og:description, og:image, twitter:card.
- curl OG URL returns 200 and a PNG visibly containing the quote and attribution.
- Topic URL loading reproduces manual search results.
- Share destinations contain correctly encoded text and canonical URL.
- Mobile layout remains intact; ShareBar wraps. Check Lighthouse mobile layout.
- No new Elasticsearch writes.

## F2 — Saved quotes and reminder digest through Elastic Workflows

### Context and outcome

Read elastic/setup.py, elastic/workflows/follow_topic.yaml, daily_hansard.yaml, and the POST /api/follow Workflow run helper. Environment: ES_URL, KIBANA_URL, ES_API_KEY, EMAIL_CONNECTOR_ID, ES_VERSION. Users save verified individual quotes to an email address, choose a reminder date, and optionally receive monthly digests. Email is the only personal field.

### Requirements

1. Add `elastic/mappings/saved_quotes.json` and setup registration. Fields:
   - keyword: email, speaker_id, speaker_name, party, topic, quote_hash, house, url
   - text: quote
   - date: date, remind_on, created_at, sent_at (nullable), last_sent
   - boolean: monthly
2. quote_hash is SHA-256 of speaker_id + quote. Use quote_hash plus email as document _id for idempotent saves.
3. `elastic/workflows/save_quote.yaml`: manual trigger; inputs email, speaker_id, speaker_name, party, topic, quote, date, house, url, remind_on, monthly. Inputs belong under trigger on 9.5+, top-level on 9.4; inspect ES_VERSION. Index into saved_quotes, set created_at to execution.startedAt, then console confirmation.
4. Register Workflow tool save_quote and assign it to the on-the-record agent so chat can save a quote.
5. `elastic/workflows/reminder_digest.yaml`: daily schedule `every: "1d"`, plus manual trigger with optional as_of and email inputs.
6. Search unsent quotes due by as_of, or monthly quotes when day-of-month is 1. Two searches and merge are allowed. Group by email with data.aggregate/data.map, then foreach email group. Sort quotes newest first.
7. Plain-text email format:

   ```text
   Your saved Hansard quotes

   <Speaker name> (<party>) on <topic>
   "<quote>"
   <DD Mon YYYY>, <House|Senate> — <url>

   ... one block per quote, newest first ...

   Source: Parliament of Australia Hansard via OpenAustralia.
   You received this because you saved these quotes on On the Record.
   ```

8. Send through kibana.request POST `/api/actions/connector/<<EMAIL_CONNECTOR_ID>>/_execute` with params.to array, subject `Your saved Hansard quotes`, and message body. After success set sent_at to execution.startedAt; monthly documents leave sent_at null and update last_sent. No LLM in digest generation.
9. POST /api/save-quote validates email and verifies the submitted quote and URL against an item returned by the server. Use item ID plus server cache, or re-run verify_quote through POST `{KIBANA_URL}/api/agent_builder/tools/_execute` with tool_id verify_quote and speaker_id/quote tool_params. Reject tampering; run save_quote only after verification.
10. GET /api/saved?email= lists saved quotes for the confirmation page. DELETE on that endpoint removes all matching documents through delete-by-query.
11. Bookmark icon on each timeline card opens email/date/monthly popover. Remember email in localStorage only. Default date from NEXT_PUBLIC_REMINDER_DEFAULT; document it in .env.example using a plausible configurable pre-election date. Success toast.
12. Footer Saved quotes link opens /saved?email=. Page lists quotes, Remove all, and Send me the digest now. POST /api/digest-now invokes reminder_digest for that email with as_of=now.
13. Popover privacy copy: `We store only your email and the quotes you save, to send the reminder. Remove them any time from the Saved quotes page.`

### Required verification

- setup creates saved_quotes; both Workflows import successfully on configured ES_VERSION.
- Save creates one document; repeated save does not duplicate it.
- Changing one word in a quote is rejected.
- Manual digest with as_of past remind_on sends exact quote/date/URL/attribution and updates sent_at; repeat sends nothing.
- Remove all deletes the matching documents.
- Show Workflow execution log for end-to-end digest verification.

## F3 — Copy-ready petition draft and change.org hand-off

### Requirements

1. Read and reuse F5 emailTemplate.ts formatting helpers. New pure function `ui/lib/petitionTemplate.ts`.
2. Populated draft:

   ```text
   Title: Ask <Full name> to address <topic> in Parliament

   To: <Full name>, <Member for <electorate> | Senator for <state>>

   The official Hansard record shows the following statements by <Full name> on <topic>:

   - <DD Mon YYYY>, <House|Senate>: "<verbatim quote>" (<url>)
   - ... (max 3, newest first)

   [Explain here what you are asking for and why.]

   We, the undersigned, ask <Full name> to respond publicly to this request.

   Source: Parliament of Australia Hansard via OpenAustralia.
   ```

3. Empty-state title: `Ask <Full name> to speak on <topic> in Parliament`. Replace the record/list section with `The Hansard record shows no statements by <Full name> on <topic> since 1 January 2025.`
4. The user's ask always remains the literal bracketed placeholder. Do not generate a demand.
5. New `ui/components/StartPetition.tsx`: Draft a petition button alongside Write to your MP; modal with read-only title field and body textarea, Copy title, Copy body, primary new-tab link Continue on change.org to https://www.change.org/start-a-petition.
6. Show steps: `1. Click Start a petition`, `2. Paste the title and body`, `3. Add your own ask`.
7. Note: `Petitions are hosted by change.org, not by On the Record.` No petition hosting, signatures, identity collection, storage, or tracking.
8. Match WriteToMp modal styles/pattern. Extract TemplateModal.tsx only if nearly identical and the refactor takes less than 10 minutes.

### Required verification

- Unit tests for populated and empty drafts: max three, newest first, unchanged quotes, attribution, literal placeholder.
- Modal renders; copying works; change.org opens in a new tab.

## F4 — Share with friends and family, with optional Contact Picker

### Requirements

1. Extend F1 ShareBar.tsx. Read emailTemplate.ts. No contacts uploaded, stored, or logged; permission only after explicit action.
2. Button `Share with friends & family` opens a small sheet. Explanation: `Choose who to send this to from your own phone or email. We don't access or store your contacts.`
3. Primary `Choose from my apps` calls navigator.share({title, text, url}). Without support, show Copy link and Email a friend, using mailto with encoded subject/body.
4. Share text: `Thought you might want to see what <Name> has said in Parliament on <topic> — verified Hansard quotes: <url>`. Email body includes that text, URL, and attribution. Avoid accidental duplicate URL when composing.
5. Render Pick contacts only when `"contacts" in navigator && "ContactsManager" in window`. On click call navigator.contacts.select(["email", "tel"], {multiple:true}).
6. Build mailto with comma-separated selected emails. If only telephone numbers were returned, build `sms:<numbers>?body=<enc>`. Open the user's own app. Discard contact results immediately after composing URL; never send them to an API or persist in state beyond what is needed.
7. Catch cancellation/rejection and empty selection: toast `No contacts selected`, keep sheet open.
8. No UTM/referral parameters or share logging.
9. README section: `Sharing with contacts uses the device share sheet and the optional Web Contact Picker API; contacts never leave the device.`

### Required verification

- Desktop Chrome fallback includes Copy link and working mailto.
- iPhone Safari opens native share and hides Pick contacts.
- Real Android Chrome, if available: picker visible, permission interaction, mail app with chosen recipients. Device emulation alone does not establish Contact Picker support.
- Network inspection shows no request carrying contact data to application servers.
- Report unavailable real-device verification explicitly.

## F5 — Copyable Write to your MP email template

### Requirements

1. Members index fields: person_id, name, house, party, electorate, state. Timeline items: date, house, quote, url, debate_title.
2. GET /api/contact?speaker_id= returns name, email (or null), contact_url. Inspect OpenAustralia getRepresentative/getSenator response for public parliamentary email; cache member contact data in memory for process lifetime. Only official parliamentary contact details may be returned.
3. contact_url: `https://www.aph.gov.au/Senators_and_Members/Parliamentarian_Search_Results?q=<encoded name>`.
4. New pure, unit-testable `ui/lib/emailTemplate.ts` with reusable item formatting helpers. Requested populated template:

   ```text
   Subject: Question regarding your statements on <topic> in Parliament

   Dear <Full name>,

   I am a constituent in <electorate or state>. I have been reading the Hansard record of your statements on <topic>. For reference:

   - <DD Mon YYYY>, <House|Senate>: "<verbatim quote>"
     <url>
   - ... (max 3 items, newest first)

   [Write your question or comment here.]

   I would appreciate a reply.

   Kind regards,
   [Your name]
   [Your suburb and postcode]

   Source: Parliament of Australia Hansard via OpenAustralia.
   ```

5. Use full name in salutation without guessing titles. Keep placeholders literal. Empty-state record line: `The Hansard record shows no statements by you on <topic> since 1 January 2025.` Then retain the placeholder paragraph and closing.
6. New `ui/components/WriteToMp.tsx`: button under timeline next to ShareBar. Modal with read-only textarea showing subject and body, Copy email with clipboard/toast, Open in my email app.
7. mailto uses official email, encoded subject and body via encodeURIComponent. If email is null, disable mail-app action and show Find their contact details linking to contact_url.
8. Note: `This opens your own email app. Nothing is sent by On the Record.`
9. No persistence, tracking, system-sent mail, or logging of body/action.
10. Requested mailto limit approximately 1,800 body characters; requirement permits quotes shortened to 300 characters with `...` if needed, always retaining source URLs. This conflicts with the byte-for-byte rule; see unresolved items below.

### Required verification

- Unit tests: three items produce three newest-first bullets; empty variant; unchanged quotes; attribution.
- curl contact endpoint returns official email or null plus contact_url.
- Copy includes entire template and attribution.
- Mail client launches with subject/body on macOS and phone where available; disclose unavailable devices.
- No network call sends mail from application systems.

## Integration and proposed parallel work

User requested collecting all five features before development, and discussed parallel development. No implementation or agent delegation has begun.

1. Inspect repository and applicable AGENTS.md; establish shared speaker/timeline types and existing helpers.
2. Parallel work lines after interfaces are agreed:
   - Sharing: F1, followed by F4.
   - Templates: F5, followed by F3.
   - Saved quotes: F2 indices, Workflows, and API/UI components.
3. Coordinate speaker-page changes centrally, then integrate and verify all surfaces and empty states.
4. Show actual command/test outputs and distinguish passed checks from unavailable external-service or real-device checks.

## Open questions and proposed resolutions — not accepted requirement changes

- F1's exact base share text omits attribution, but completion criteria require it. Proposed: append the complete attribution.
- Speaker ID plus topic reproduces a query, not an immutable historical result when Hansard data changes. Permanent exact findings would need additional snapshot/version requirements.
- F2 email-only list/delete/digest endpoints need an access-control decision to avoid exposing or modifying another person's saved quotes. The request explicitly says this is not a login; do not silently add an authentication product.
- F2 monthly quotes need last_sent guards to avoid re-sending on repeated runs. One-off and monthly scheduling state must be coordinated to avoid duplicate sends.
- F2 as_of=now alone does not send quotes whose reminder date is in the future. Explicit immediate-send semantics need to be established for the digest-now action.
- F4's claim that the app never accesses contacts conflicts with optional explicit Contact Picker access. Proposed: explain that only chosen email/phone fields are read on explicit action and application servers never receive them.
- F4's contacts-never-leave-device wording needs to distinguish the application from the user's own mail/SMS service, which receives recipients when the user sends.
- F5's verbatim requirement conflicts with shortening quotes for mailto. Proposed: retain full original copy text, reduce quote count for mailto, and offer copying when still too long instead of silently altering quotes. This proposal has not been approved.
- F5's constituent assertion may not apply to the user. Proposed: make constituency wording a user-editable placeholder; this has not been approved.
