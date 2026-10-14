# Closed-course test sites

| Field | Value |
|---|---|
| Work product | Closed-course test site requirements and candidate list (supports [WP-V-01](../WP-V-01-safety-validation.md) OI-1 and [WP-V-07](../WP-V-07-vehicle-test-operations.md) §12) |
| Standard reference | ISO 26262-4:2018 §8 (safety validation); ISO 21448:2022 §10 (verification and validation); UL 4600 principles (test safety) |
| Version | 0.1 |
| Status | Draft: desk research only, no site contacted |
| Author | Assurance team |
| Reviewer(s) | TBD |
| Region | Atlanta GA – Greenville SC – Charlotte NC corridor (I-85) |
| Researched | 2026-10-12 |

## 1. Purpose

The vehicle tests that verify the assumptions the HARA credits (AOU-01, -02, -03, -05) and the controllability tests in [WP-V-01](../WP-V-01-safety-validation.md) run only on a closed course ([WP-V-07](../WP-V-07-vehicle-test-operations.md) level L3). This page states what a site must offer and lists candidate sites in the maintainer's region.

> [!WARNING]
> **Nothing here is confirmed.** The candidates come from public web sources dated between 2019 and 2026. No site has been contacted, no price or access term has been agreed, and no site has been assessed under the WP-V-07 §4 L3 entry criteria. A site is usable only after a written agreement and a site risk assessment.

## 2. What a site must offer

The speeds come from the WP-V-01 test specifications and the WP-V-07 §8.1 closed-course rules. Lengths are first estimates **(TBC)**; confirm them in the session test plans.

### 2.1 Test tiers

| Tier | Speeds | Tests | Minimum layout (TBC) |
|---|---|---|---|
| **T1 Low speed** | ≤ 60 km/h (VS-VAL-04 up to 80 km/h) | VS-VAL-01 EPS torque, -02 EPS message loss, -04 brake override, -05 PCM envelope, -08 PCM onset at 30 and 60 km/h, -11 lateral deviation at ≤ 50 km/h, -13 unexpected acceleration at 40 km/h, -16 loss of deceleration at 50 km/h, -20…-26 envelope fault reactions | Straight of about 400 m plus run-off, or a large paved pad; space for a 3.5 m coned lane |
| **T2 Up to 90 km/h** | 60–90 km/h (110 km/h only after a separate risk review) | VS-VAL-03 driver override at 90 km/h, -10 lateral disturbance in a coned lane at 30–90 km/h, -12 loss of lateral control in a curve at 50 and 70 km/h, -14 deceleration step at 60 and 90 km/h, -08 PCM onset at 90 km/h, -15 release on driver input at 30/60/90 km/h | Straight of about 1 km, or a loop with long straights; gentle curves of known radius for VS-VAL-12; run-off along the test lane |
| **T3 Soft targets** | Stock PCS and following speeds | VS-VAL-06 stock PCS/AEB preservation (AOU-04, SG-07), -13, -16 | Permission to use radar-reflective soft targets (and a target carrier if hired); straight long enough to reach PCS test speeds |

### 2.2 Conditions every site must meet

| # | Condition | Why |
|---|---|---|
| S-1 | Exclusive use of the test area during runs, with access control | WP-V-07 §8.1 clearance rule |
| S-2 | Written permission to test an aftermarket driver-assistance device, including closed-course firmware builds and fault injection | WP-V-07 §7.4 |
| S-3 | Insurance that covers development testing of an aftermarket device, or a site policy that accepts the project's cover | WP-V-07 §12, OI-4 |
| S-4 | Range safety officer or site staff, emergency access and a site risk assessment | WP-V-07 §2 (RSO) and §4 L3 entry criteria |
| S-5 | Data logging and video recording allowed on site | WP-V-07 §11 |
| S-6 | Paved surface; painted lane lines preferred (the driving model needs road edges or lines to engage normally), cones allowed | VS-VAL-10 coned lane; normal engagement |
| S-7 | Night running and a wet surface (sprinkled or natural) available, for a subset of tests | VS-VAL-43 |
| S-8 | Within a day trip of the corridor, or bookable as a multi-day campaign | Practicality |

## 3. Candidates in the corridor

"Likely tiers" is a reading of the public description against §2, not a confirmation. Phone numbers are as published by the sources below and must be checked.

| ID | Site | Location | What public sources say | Likely tiers | Notes | Priority |
|---|---|---|---|---|---|---|
| TS-01 | **International Transportation Innovation Center (ITIC)** | SC Technology and Aviation Center, Greenville SC | Independent proving ground for OEMs, suppliers and universities; 1-mile asphalt straightaway, 1,000 ft brake lane, durability track, slope hills; half- or full-day rental, 24/7; a ~3-mile highway-speed loop reported as built or in development (sources disagree) | T1, T2, probably T3 | Purpose-built for vehicle testing and central in the corridor. Ask about the loop's status, soft-target use and S-2. Phone listed as 864-900-2419 | **1** |
| TS-02 | **Michelin Laurens Proving Grounds** | Laurens SC (~45 min from Greenville) | 3,200 acres, more than a dozen wet, dry and off-road tracks, coast-down track, year-round rental, 24/7 security, garages with lifts | T1, T2, T3 (to confirm) | Full proving ground, likely the most capable and the most expensive. Phone listed as 864-683-1333 | **1** |
| TS-03 | Michelin Raceway Road Atlanta | Braselton GA (~1 h NE of Atlanta) | Circuit rentable throughout the year; Grand Prix course, skid pad and autocross area | T1 (skid pad, autocross); T2 on the circuit only if lane-free running is acceptable | Good for low-speed sessions near Atlanta. No lane lines on a race circuit | 2 |
| TS-04 | Atlanta Motorsports Park | Dawsonville GA | 2-mile, 16-turn road course with several configurations; private and corporate rentals; listings mention research and testing | T1, partly T2 | Ask whether the paddock or a straight can host a coned lane. Phone listed as 706-344-1235 | 3 |
| TS-05 | Atlanta Motor Speedway | Hampton GA | 1.5-mile quad oval, quarter-mile short track, three road-course configurations; rentals marketed mainly for events | T1, T2 (oval banking to be checked) | Testing terms unknown | 3 |
| TS-06 | Charlotte Motor Speedway and zMAX Dragway | Concord NC | Oval and roval have been rented for private sessions in the past; zMAX is a four-lane concrete drag strip | T1 (straight-line tests on the drag strip) | Current rental terms unknown; drag-strip length may limit T2. zMAX phone listed as 704-455-3209 | 3 |
| TS-07 | Carolina Motorsports Park | Kershaw SC (~1.5 h SE of Charlotte) | Road course and kart track; track days and garage rentals | T1, partly T2 | Private rental terms not published | 4 |
| TS-08 | NCAT Test Track (Auburn University) | Opelika AL (~2 h SW of Atlanta) | 1.7-mile oval used for pavement research and autonomous-vehicle and truck-platooning studies by Auburn's GAVLAB; garage and observation building | T2 | Research-partnership route, not a commercial rental. Worth an approach if a university partner is wanted | 3 |

### 3.1 Not a closed course

| Site | Location | Why it is not L3 |
|---|---|---|
| Curiosity Lab at Peachtree Corners | Peachtree Corners GA | A free autonomous-vehicle test route of about 1.5 miles on the public streets of an office park. WP-V-07 treats it as a public road, so only L4/L5 use applies unless the city closes the route. Useful later for restricted public-road testing |

### 3.2 Outside the corridor, for reference

| Site | Location | Note |
|---|---|---|
| NC Turnpike Authority, Triangle Expressway | Research Triangle NC | Proposed as a federally designated automated-vehicle proving ground; current status not confirmed |
| NC Center for Automotive Research | Garysburg NC | Independent test site, described as off-road focused |

## 4. Recommendation

1. **Contact TS-01 (ITIC) and TS-02 (Michelin Laurens) first.** Both are real proving grounds near Greenville, the middle of the corridor, and both appear to cover T1 and T2.
2. **Keep TS-03 (Road Atlanta skid pad) as the low-speed option near Atlanta** if the proving grounds are too costly for early T1 sessions.
3. **Approach TS-08 (NCAT/Auburn)** only if a university partnership becomes part of the plan, for example for an independent reviewer or test subjects.

## 5. Questions for each site

Ask these in the first contact and record the answers in §6:

1. Is the site available for testing an aftermarket driver-assistance device on a production car, including modified-firmware runs (S-2)?
2. Which areas can be booked exclusively, and what are their lengths, widths and run-off (T1, T2)?
3. Are radar-reflective soft targets allowed, and does the site hire target systems (T3)?
4. Are lane lines painted anywhere, and may cones be placed?
5. What insurance does the site require (S-3)?
6. Is site staff or a range safety officer included (S-4)?
7. Are logging and video allowed (S-5)? Are night runs and a wet surface available (S-7)?
8. Price per half day and full day, and lead time for booking.

## 6. Contact log

| Date | Site | Who | Outcome | Next step |
|---|---|---|---|---|
| — | — | — | No site contacted yet | Contact TS-01 and TS-02 |

When a site is confirmed, record it here with its agreement reference, then close [WP-V-01](../WP-V-01-safety-validation.md) OI-1 and update the site entries in [WP-V-07](../WP-V-07-vehicle-test-operations.md) §12.

## 7. Sources

Retrieved 2026-10-12. Dates of the underlying pages vary, and several describe plans that may have changed.

- ITIC: [Upstate SC Alliance, "ITIC: South Carolina's World-Class Automotive Test Track"](https://www.upstatescalliance.com/itic-south-carolinas-world-class-automotive-test-track/) · [ITIC, About](https://itic-sc.com/about/) · [ITIC, Slope Hill track](https://itic-sc.com/itic-slope-hill-now-open-for-testing/) · [Automotive Testing Technology International, "Expansion at ITIC"](https://www.automotivetestingtechnologyinternational.com/features/expansion-at-itic.html) · [SCTAC](https://sc-tac.com/) · [Greenville Chamber listing](https://www.greenvillechamber.org/membership/itic-international-transportation-innovation-center/)
- Michelin Laurens Proving Grounds: [Michelin Engineering and Services, Laurens track rental](https://engineering-and-services.michelin.com/tracks-rental/laurens) · [Tracks rental](https://engineering-and-services.michelin.com/tracks-rental)
- Michelin Raceway Road Atlanta: [Track rental](https://michelinracewayroadatlanta.com/track-info/about-mrra/track-rental)
- Atlanta Motorsports Park: [Explore Georgia listing](https://exploregeorgia.org/dawsonville/sports-racing/motorsports-attractions-facilities/atlanta-motorsports-park) · [SCCA location page](https://www.scca.com/locations/1981686-atlanta-motorsports-park)
- Atlanta Motor Speedway: [Track rental](https://www.atlantamotorspeedway.com/business/track-rental)
- Charlotte Motor Speedway and zMAX Dragway: [Jayski, 2011 private rental](https://www.jayski.com/2011/02/04/hendrick-motorsports-rent-cms-for-pit-practice/) · [zMAX Dragway (Wikipedia)](https://en.wikipedia.org/wiki/ZMax_Dragway)
- Carolina Motorsports Park: [SCCA location page](https://timetrials.scca.com/locations/1984324-carolina-motorsports-park)
- NCAT and GAVLAB: [Auburn GAVLAB resources](https://eng.auburn.edu/sites/gavlab/research/resources) · [Trucknews, "Auburn University opens autonomous vehicle lab"](https://www.trucknews.com/equipment/auburn-university-opens-autonomous-vehicle-lab/1003149003)
- Curiosity Lab: [City of Peachtree Corners](https://peachtreecornersga.gov/278/Curiosity-Lab-at-Peachtree-Corners)
- North Carolina: [NCDOT, Autonomous Vehicle Testing and Research in NC (2018)](https://connect.ncdot.gov/groups/echs/Documents/2018/Autonomous%20Vehicle%20Testing%20and%20Research%20in%20NC%20(9-7-18).pdf) · [Transport Topics, NC Turnpike Authority](https://www.ttnews.com/articles/self-driving-cars-are-north-carolina-turnpike-authoritys-radar)
