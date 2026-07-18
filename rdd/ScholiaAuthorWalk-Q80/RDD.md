# ScholiaAuthorWalk-Q80

First [Reel Driven Development](https://cr.bitplan.com/index.php/Reel_Driven_Development_-_RDD) reel for the nicescholia migration — an author aspect walk for [Tim Berners-Lee (Q80)](https://www.wikidata.org/wiki/Q80), applying [named parameterized queries](https://snapquery.bitplan.com/) and the [Y-Principle](https://wiki.bitplan.com/index.php/Y-Prinzip).

- Recorded: 2026-07-18 13:22 CEST, 3:54 min, QuickTime screen recording
- Mishap: audio forgotten (no narration track) — AI-fixed by reverse RDD: narration inferred from a dense frame sweep

## Artifacts

| artifact | file |
|----------|------|
| video (web-readable, 1792px/30fps re-encode of the original mov) | [ScholiaAuthorWalk-Q80.mp4](ScholiaAuthorWalk-Q80.mp4) |
| transcript (AI-inferred narration — hypothesis, no audio existed) | [ScholiaAuthorWalk-Q80-transcript.txt](ScholiaAuthorWalk-Q80-transcript.txt) |
| 17 hop screenshots | [screenshots/](screenshots/) |

## Results

- General RDD introduction: [discussion #11](https://github.com/WolfgangFahl/nicescholia/discussions/11)
- This reel walked hop by hop with screenshots and findings: [discussion #12](https://github.com/WolfgangFahl/nicescholia/discussions/12)
- Findings → actionable issues in three trackers:
  1. **scholia**: F3 Use aspect empty → existing [WDscholia/scholia#1591](https://github.com/WDscholia/scholia/issues/1591) (Use-aspect curation, missing-data), related [#2780](https://github.com/WDscholia/scholia/issues/2780) (no-results class on QLever); F4 legacy load = the announced WDQS graph-split migration, related [#2769](https://github.com/WDscholia/scholia/issues/2769) — no new issues filed to avoid duplicates
  2. **snapquery**: F1 error format → [WolfgangFahl/snapquery#79](https://github.com/WolfgangFahl/snapquery/issues/79); F2 prefix merger → [WolfgangFahl/snapquery#80](https://github.com/WolfgangFahl/snapquery/issues/80)
  3. **nicescholia**: the author aspect should now have a POC → [#13](https://github.com/WolfgangFahl/nicescholia/issues/13) (milestone 0.1.0); dashboard & API surfaces: [#8](https://github.com/WolfgangFahl/nicescholia/issues/8), [#9](https://github.com/WolfgangFahl/nicescholia/issues/9), [#10](https://github.com/WolfgangFahl/nicescholia/issues/10)
