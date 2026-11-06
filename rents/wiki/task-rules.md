# Task rules (as published)

Source: https://www.microburbs.com.au/p/hackathon-task-rents (read via a web-fetch tool that SUMMARISES pages, so wording is paraphrased: re-read the page itself on the day, especially the constraint lines).

## Objective
Estimate weekly rent for every flat, **with and without a car space**. ("Help tenants and landlords estimate weekly rent for every flat, with or without parking.")

## Inputs
- `rents-input-flats-city-of-sydney.csv` (public): **65,777 flats across 33 suburbs**, each with a G-NAF `gnaf_id`. Keep ALL rows, including **4,246 addresses absent from the City address and block files**.
- `rents-past-leases-city-of-sydney.csv` (**private**, day-of only): historic adverts.
- `blocks-homes-and-people-2021-2026.csv` (**private**, day-of only): 2021 Census counts and 2026 estimates, per ABS mesh block.
- API endpoints `rent-history` and `rent-history-latest` return past adverts; **no as-of switch**, you must filter by date yourself.
- The `for-rent` listings endpoint is later than the task date and **cannot be used**.
- Other open data is allowed provided you have the right to use it.
- Private files: use on the day only, must not be republished.

## Deliverables
1. `rents_<team>.csv`: one row per flat: `gnaf_id`, `rent_with_car_space`, `rent_without_car_space`. All 65,777 IDs, no extras, no blank values.
2. `report.html`: lead with insights found along the way; then held-out accuracy score and R squared; how adverts were split by date; data and method used.

## Constraints
- Use only information dated by **31 July 2026**.
- Build on earlier adverts, check against later ones (dated by 31 Jul). "Never use those later adverts while building or tuning your method."
- The supplied 2026 block estimates may be used.

## Judging
- Rank by **median absolute dollar error**; tie-break by **share of estimates within $100**.
- Scored on **1,699 adverts dated 1 Aug – 30 Sep 2026** (hidden).
- The scored rent matches the advert's parking; if blank, the input's parking is used. Adverts excluded only when both unknown.
- "Empty scored answers count worse than answered errors." -> never leave blanks.
- Baseline: the page's baseline rental valuation missed by **$86/week** and placed **55.21%** of adverts within $100. Beat this.

## Timing (CORRECTED by the user)
- The task page says team files are "sent at 11 am on Saturday 7 November 2026" (the page does not state a submission deadline/channel).
- **The user confirmed: input files + key arrive at 11:00; the submission deadline is 15:00 the same day.** = 4 hours. (Earlier in the conversation Claude wrongly treated 11 am as the deadline.)
- Submission channel: still unknown -> ask organisers.

## Plain-English reading of each sentence
- *"Add rents_<team>.csv with all 65,777 G-NAF address IDs."* The answer file; one row per input flat, each with two predicted weekly rents.
- *"Lead with insights you found along the way."* Start the report with findings (e.g. car-space premium by suburb), then the method.
- *"Held-out accuracy score and R squared."* Held-out = measured on adverts the model never saw while being built. Accuracy = median absolute $ error (+ share within $100). R squared = share of variation in rent explained; 1 - (model squared errors / squared errors of always guessing the mean).
- *"Explain how you split adverts by date for your own check."* Time-based split (not random): earlier adverts build, later ones check. State the exact cut-off date.
- *"Use earlier adverts to build... check against later adverts dated by 31 July 2026."* Build pile = earlier; check pile = later but still <= 31 Jul.
- *"Never use those later adverts while building or tuning."* The check pile is for checking only: no training on it, no tuning settings after looking at its score.
- *"Show the data and method you used."* List sources (endpoints, supplied files, other open data) and describe model/features.

## What "test" means (clarified)
- Your own check: adverts up to 31 Jul only (e.g. 1 Jun - 31 Jul). Never Aug/Sep.
- The official test: the organisers' hidden 1 Aug - 30 Sep adverts. You never see them. Nothing after 31 Jul is usable anywhere.
- The API does NOT enforce the cutoff: the spec's example advert is dated 2026-10-28. Excluding later data is our responsibility.
