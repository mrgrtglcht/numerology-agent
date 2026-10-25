# TikTok photo music migration — 2026-10-24

## Activation verified 2026-10-25

The owner connected quanta.aura, supplied the GitHub secret and confirmed removing
both old silent TikToks. Creator-info confirmed PUBLIC_TO_EVERYONE.
Part 1 was posted once with auto_add_music=true; TikTok returned publish_complete:
https://www.tiktok.com/@quanta.aura/video/7700534302198615326
Part 2 is queued once for 2026-10-30 22:27 Europe/Warsaw, schedule ID
ba181946-9c33-458f-9acd-701f02be43e7. Readback confirmed all seven images,
caption, public visibility and auto_add_music=true in scheduled.payload.
The queue was reconciled without resending (Actions run 40181134859).
Both canonical deliveries now use provider postwire and retain old Buffer history.
cloud.yml now defaults to postwire; future slots are Friday 22:27 / Sunday 09:46.
110 local tests pass, including the observed nested schedule schema and lowercase
publish_complete status. Playback verification remains with the owner: TikTok's
browser page displayed a CAPTCHA. Do not claim the sound was audibly checked.

The following section records preparation history before activation.

Music-free Buffer publishing is paused by TIKTOK_REQUIRE_MUSIC=true in cloud.yml.
Telegram remains independent. Published parts 1 and 2 are retained.
Part 3 was returned to a Buffer draft, retaining all seven images.

PostWire's published Free plan includes 10 posts/month, three scheduled at once,
and API access. Primary references checked 2026-10-24:

- https://postwire.io/pricing/
- https://postwire.io/docs/
- https://postwire.io/docs/network-options/
- https://postwire.io/docs/scheduling/

The adapter requests public visibility and auto_add_music=true explicitly.
It checks the connected handle quanta.aura and allowed public visibility first.
It schedules Friday 22:27 / Sunday 09:46 Europe/Warsaw, handles DST, retains at
most two waiting posts, and caps its own reservations at ten per calendar month.
Other posts created manually can consume the service quota too; service holds
are errors, never successful scheduling. No automatic upgrade or paid request.

Activation still requires the owner to register a Free PostWire account, verify
email, connect TikTok via OAuth and save POSTWIRE_API_KEY in GitHub Actions secrets.
Then check the creator-info response and switch repository variable
TIKTOK_PUBLISHER=postwire. POSTWIRE_BRAND_ID is optional for a single brand.
Do not reactivate Buffer for TikTok: that API has no auto_add_music control.

Before declaring migration complete, run a real connection check and schedule
part 3, read back all seven images plus music/public options, and inspect the first
published post's sound and visibility. This has NOT been tested against an
authenticated PostWire account yet. If the returned record does not expose the
documented media/options, the adapter preserves the ID and stops for review.
Unknown sends are never repeated. Only positive per-network results update the
content journal to published. Music is requested, not proof of recommendations.

The successful source-recovery preview is GitHub Actions run 40083563339.
Part 4 is prepared under cloud-tiktok-2026-10-24-preview/part-04, not published.
