# India crop and rotation model plan

Source/access review: **2026-11-15**. Development branch: **`backend-ai`**.
Status: **planning and source sampling, not a trained Indian recommendation model**.

## 1. Recommended direction and boundaries

Build an India-wide crop catalogue and collect geographically varied Indian data, with a Karnataka-first application pilot. Train several small, comparable models rather than one large model. Start with a baseline, CatBoost and a small embedding MLP; add temporal and attention-based models only when the corresponding data exist.

The first output should distinguish **reference crop suitability**, **expected regional crop outcomes**, and eventually **field rotation outcomes**. These are different learning tasks. A softmax can express relative preference among supported candidates, but it cannot turn missing best-crop labels into a probability of farming success.

The current UK pilot supplies reusable acquisition, provenance, dataset and training machinery. Its four fitted crop models, two UK sites and retrospective evaluation do **not** establish suitability for India. Preserve its versioned artifacts; create separate Indian datasets and model registrations.

This plan complements [Plan.md](Plan.md), not its 297-family inventory or S01-S11 completion gates. Scientific sign-off is not required for engineering health under the current override. Authenticity, units, nonredundancy, working acquisition, honest missingness and leakage-safe evaluation remain required. No locally generated DSSAT/APSIM outcomes, random environments, fabricated crop labels or augmented agricultural observations will be used.

**Recommended scope progression:** annual field crops, then short-cycle horticulture, then perennial/orchard models, then learned multi-season rotation comparisons. Do not put orchard establishment and next-season grain planting into one unqualified softmax.

## 2. Source audit: what each dataset can actually contribute

Access statements below describe the reviewed route and date, not a guarantee of future uptime. A working catalogue page is not proof that its full training data can be downloaded.

| Source | Data role and useful content | Verified access and remaining work |
| --- | --- | --- |
| [FAO EcoCrop][eco] | Versioned, published crop requirements: temperature, annual water/rainfall, pH, soil categories, altitude, photoperiod and crop cycle. Crop-trait inputs and reference compatibility, not observed yield or best-crop labels. | The public [production application][eco-home] works. Archived its 2,568-name global catalogue and 25 requirement sheets. The older `ecocrop.review.fao.org` route redirects to sign-in. Build a maintained normalizer; retain source IDs and references. Catalogue metadata lists CC-BY-4.0; preserve attribution and check any linked material's terms. |
| [FAO GAEZ v5][gaez] | Published model-derived suitability and attainable yield for specified crops, climate periods, water regimes and input/management levels. A potential reference-suitability training target, not field observations. | Overview and portal are accessible; Indian crop rasters and their download/readback have not yet been verified. V5, released in 2025, includes additions such as mango, cashew, avocado, watermelon, sesame and finger millet. Verify the actual crop-code inventory before admitting classes. |
| [DSSAT][dssat] | Crop/cultivar parameters, daily weather, layered soil and management definitions; licensed observed experiment/evaluation datasets where available. | About page accessible; the models landing page is largely a placeholder. More than 45 crop models are described, but the exact release/crop roster and download rights must be pinned. Simulated yields are not observed labels and will not populate this corpus. |
| [APSIM][apsim] | Crop/soil/management structures and authentic observed validation experiments; potentially useful for real rotation evidence. | Next Generation documentation accessible. Some Classic crop/license pages returned 403. Do not assume Classic and Next Generation support identical crops. Confirm version, experiment-data rights and intended-use licence before acquisition. No simulations were run. |
| [ICRISAT VDSA][vdsa] | Potentially valuable plot lists, cropping patterns, cultivation schedules, rainfall and repeated farm observations; meso agricultural statistics also exist. | Portal and documentation accessible, but microdata require login/registration. No plot survey files acquired. Separate SAT India, East India and Bangladesh records. This is a promising rotation source, not an already available nationwide label set. |
| [FAOSTAT crop production][faostat] | Country/year/crop area, production and yield; national crop-presence checks, trend context and aggregation QA. Preserve official/estimated/imputed flags. | Catalogue and item schema accessible; a current India-filtered production extract is still required. Reviewed metadata spans 1961-2024. National annual rows cannot become district, field or seasonal observations. The older item schema is not current India-presence proof. |
| [Indian DES APY reports][des] and [UPAg][upag] | District/state, crop, season and agricultural-year area/production/yield: the preferred broad Indian outcome corpus. | DES report selectors accessible. UPAg is largely client-rendered in direct requests; actual exports remain to be verified. Data.gov.in access returned 403. Use documented exports or an authorized API; report access blocks rather than substitute unofficial or generated data. |
| [NHB statistics][nhb-stats] and [crop project references][nhb] | Indian horticultural crop presence, published growing conditions, and real statistical fruit/vegetable outcomes where available. | Crop reference pages accessible. The indexed `FinalEstimates.xls` is a historical 2010-11 resource, not current statistics; its tabular import remains unverified. Separate final and advance estimates. Bankable-project projected yields/costs are assumptions, not observed training labels. |
| [Indian crop calendar][calendar], ICAR/state agricultural-university guidance and dated farmer records | Region/crop sowing windows, production systems, cultivars, phenology and management constraints. | Calendar landing page accessible; machine-readable region/crop records still need acquisition and validation. Acquire identifiable official publications, not unsourced universal planting-month lists. |
| [NASA POWER][power] | Daily temperature, rainfall, humidity, wind and solar radiation; the existing pipeline already handles these seven variables at authentic UK sites. | Reuse the acquisition path, but prove coverage and metadata at Indian locations and dates. A working UK request does not validate every Indian grid/time window. |
| [SoilGrids][soilgrids], dated laboratory reports and farmer observations | Soil pH, texture, SOC and other supported properties; actual measurements for drainage, salinity, effective depth and management where available. | SoilGrids documents 250 m mapped estimates and six depth intervals. Its REST service is paused; documented WCS/WebDAV alternatives still need a real sample/download proof. Mapped estimates are not contemporaneous field measurements. |

Additional sources to investigate only for a specific missing input: SMAP soil moisture, GPM rainfall, Landsat/MODIS vegetation, ECOSTRESS thermal/ET products, NASA elevation, IMD or licensed station observations, and hourly ERA5-Land for chilling. They are **candidates**, not verified integrations. Avoid acquiring overlapping products merely to increase feature counts.

For every acquired source, record the licence, version/revision, spatial support, temporal support, units, flags and redistribution restrictions. Do not place credentials, restricted survey microdata or unlicensed redistributable bundles in Git. FAOSTAT and Indian statistics may share underlying reports; they are not automatically independent evidence.

## 3. India crop catalogue and staged inclusion

The global EcoCrop list is a discovery aid, **not 2,568 crops verified for India**. Use a canonical crop/use registry, preserving provider codes and names. Each candidate needs: Indian cultivation evidence, an unambiguous crop/product mapping, a growing-requirement profile, compatible features, and sufficient labels for its intended task.

### 3.1 Initial annual field-crop shortlist

Start intake with rice, wheat, grain maize, sorghum/jowar, pearl millet/bajra, finger millet/ragi, chickpea/gram, pigeonpea/tur, green gram/moong, groundnut, soybean and rapeseed-mustard.

These are **12 proposed reporting groups**, not 12 automatically trainable classes. In particular:

- Keep paddy rice, milled rice, grain maize and forage maize separate by product/yield basis.
- A statistics item named rapeseed-mustard may combine species. EcoCrop `548` is *Brassica juncea*, not a profile for the entire group. Retain the aggregate label or obtain real disaggregation; never assign its yield to invented species-level records.
- Resolve local/common-name aliases once. Preserve species, cultivar, irrigation system and production use when known; do not invent them when a source only names a commodity.
- Learn from multiple Indian districts, seasons and years. Karnataka-first deployment does not mean training only on Karnataka or recommending every catalogue crop there.

### 3.2 Wider India-facing intake queue

This is a broad candidate list, not an exhaustive flora inventory or a claim that every entry already has usable labels. The sources in the last column are where inclusion must be substantiated; a globally listed species alone does not pass the India gate.

| Group | Candidate crops/vegetation | Evidence path and separation needed |
| --- | --- | --- |
| Additional cereals and millets | Barley, oats, foxtail millet, little millet, kodo millet, barnyard millet, proso millet, buckwheat | Indian statistics/ICAR calendars plus EcoCrop; distinguish grain and forage. |
| Additional pulses | Black gram/urad, lentil/masur, field pea, cowpea, horse gram, moth bean, common bean/rajma, lablab | DES/VDSA/official guidance plus EcoCrop; green pods and dry pulses are different products. |
| Additional oilseeds | Sesame, sunflower, safflower, castor, linseed, niger; separately identified rapeseed/mustard species | Indian statistics and crop-specific profiles; no species splitting of aggregate outcomes. |
| Vegetables and roots | Tomato, brinjal, okra, onion, garlic, potato, cabbage, cauliflower, green peas, French bean, carrot, radish, beetroot, sweet potato, cassava/tapioca, colocasia, yam | NHB/Indian horticultural statistics and official crop guidance; distinguish fresh market, seed, leaf and storage-organ targets. |
| Cucurbits and leafy crops | Cucumber, watermelon, muskmelon, bottle gourd, bitter gourd, ridge gourd, sponge gourd, ash gourd, pumpkin, amaranth, spinach, fenugreek leaf | NHB/state horticulture/ICAR and EcoCrop; protected cultivation needs its own environment/management inputs. |
| Fruits covered by the reviewed NHB index | Apple, banana, aonla/amla, mango, guava, orange, papaya, sapota, pineapple, litchi, ber, pomegranate, strawberry, kiwi, passion fruit, grape | Indian crop-reference presence verified by NHB. Outcome history and cultivar-specific conditions remain separate gates. Distinguish sweet orange, mandarin, acid lime and lemon in later citrus intake. |
| Plantation and other fruit candidates | Coconut, arecanut, cashew, tea, coffee, rubber; jackfruit and other regionally documented fruit crops | Indian commodity boards/official statistics and crop profiles. Separate perennial establishment, mature production and ratoon/replanting systems. |
| Spices, aromatics and commercial crops | Chilli, turmeric, ginger, coriander, cumin, fennel, fenugreek seed, black pepper, cardamom; lemongrass, mint, patchouli, celery; cotton, sugarcane, jute | Official crop/commodity sources; NHB directly lists the four aromatic/herb project references. Multi-cut, ratoon and long-duration systems cannot inherit an annual cereal target. |
| Forage, cover and green-manure crops | Fodder sorghum/maize/oats, cowpea, berseem, lucerne, Napier grass, sunn hemp, dhaincha | Real forage/rotation trials and official profiles. Record biomass basis and actual soil/rotation responses; species traits alone do not establish a field-level nitrogen benefit. |

Mushrooms require a separate controlled-environment task; beekeeping is not a crop class. Neither belongs in an outdoor soil/weather crop softmax.

Fruit crops must not be a token addition to an annual dataset: banana, papaya and pineapple need establishment/ratoon or multi-year context; mango, apple, citrus and other orchards need age, cultivar, phenology and a longer planning horizon. Strawberry can be managed as a short-cycle crop despite perennial biology. The production system, not a single lifespan label, selects the model.

### 3.3 Actual requirement sheets sampled for this plan

The following **25 authentic EcoCrop profiles** were archived and their source identities checked: 12 field-crop identifiers, five vegetable identifiers and eight fruit identifiers. These are published parameters, **not 25 trained classes or observed Indian crop-season records**.

Numbers below reproduce the source's **optimal / absolute** ranges. They are broad reference ranges, not universal kill thresholds or cultivar-specific prescriptions. Temperature is in degrees Celsius; water/rainfall is in mm per year; pH is dimensionless. EcoCrop's [temperature help][eco-temp] asks for average minimum/maximum conditions during the growing season; its [rainfall help][eco-rain] explicitly allows supplemental irrigation/other water. Do not compare these columns with an arbitrary recent-month temperature extreme or a 90-day rain total.

| Candidate and EcoCrop ID | Temperature: optimal / absolute | Annual water/rainfall: optimal / absolute | pH: optimal / absolute |
| --- | --- | --- | --- |
| Rice [1574](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=1574) | 20-30 / 10-36 | 1500-2000 / 1000-4000 | 5.5-7 / 4.5-9 |
| Wheat [2114](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=2114) | 15-23 / 5-27 | 750-900 / 300-1600 | 6-7 / 5.5-8.5 |
| Maize [2175](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=2175) | 18-33 / 10-47 | 600-1200 / 400-1800 | 5-7 / 4.5-8.5 |
| Sorghum [48747](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=48747) | 22-35 / 8-40 | 400-600 / 300-700 | 5.5-7.5 / 5-8 |
| Pearl millet [8418](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=8418) | 25-35 / 12-40 | 400-900 / 200-1700 | 5-6.5 / 4.5-8.3 |
| Finger millet [5657](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=5657) | 18-30 / 8-35 | 500-1100 / 300-4300 | 6-7 / 5.5-8.2 |
| Chickpea [2479](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=2479) | 15-29 / 7-35 | 600-1000 / 300-1800 | 6-8.5 / 4.7-9.5 |
| Pigeonpea [576](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=576) | 18-38 / 10-45 | 600-1500 / 400-4000 | 5-7 / 4.5-8.4 |
| Green gram [2150](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=2150) | 21-36 / 8-40 | 650-900 / 500-1250 | 5.5-6.2 / 4.3-8.3 |
| Groundnut [2199](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=2199) | 22-32 / 10-45 | 600-1500 / 400-4000 | 5.5-6.5 / 4.5-8.5 |
| Soybean [1150](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=1150) | 20-33 / 10-38 | 600-1500 / 450-1800 | 5.5-6.5 / 4.5-8.4 |
| Indian mustard [548](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=548) | 15-28 / 7-40 | 700-2400 / 500-4200 | 5.5-6.5 / 5-8 |
| Tomato [1379](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=1379) | 20-27 / 7-35 | 600-1300 / 400-1800 | 5.5-6.8 / 5-7.5 |
| Okra [289](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=289) | 20-30 / 12-35 | 600-1200 / 300-2500 | 5.5-7 / 4.5-8.7 |
| Onion [364](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=364) | 12-25 / 4-30 | 350-600 / 300-2800 | 6-7 / 4.3-8.3 |
| Potato [1971](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=1971) | 15-25 / 7-30 | 500-800 / 250-2000 | 5-6.2 / 4.2-8.5 |
| Cabbage [554](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=554) | 15-24 / 7-32 | 500-1000 / 300-2500 | 6-7.5 / 5-8.3 |
| Mango [1416](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=1416) | 24-30 / 8-48 | 600-1500 / 300-2600 | 5.5-7.5 / 4.3-8.5 |
| Hybrid banana [7849](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=7849) | 25-35 / 15-40 | 1400-2400 / 1000-5000 | 5.5-6.5 / 4.5-8 |
| Guava [1804](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=1804) | 20-33 / 10-45 | 1000-3000 / 400-5000 | 5.5-7.5 / 4-8.5 |
| Papaya [630](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=630) | 21-30 / 12-44 | 1500-2500 / 1000-3000 | 5.5-7 / 4.5-8 |
| Apple [1407](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=1407) | 14-27 / 8-33 | 700-2500 / 500-3200 | 6-7 / 4.5-8 |
| Commercial strawberry [1112](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=1112) | 11-24 / 6-28 | 600-900 / 300-1700 | 6-6.8 / 4.5-8.2 |
| Pineapple [402](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=402) | 21-30 / 10-36 | 800-2500 / 550-3500 | 4.5-8 / 3.5-9 |
| Grape [2160](https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=2160) | 18-30 / 10-38 | 700-850 / 400-1200 | 5.5-7.5 / 4.5-8.5 |

The archived sheets also preserve depth, texture, drainage, fertility, salinity, altitude, photoperiod, life span, crop cycle and missing entries. Examples of issues that the normalizer must **not hide**:

- Rice's sheet describes a wet-rice system and poorly drained conditions; most sampled vegetables specify well-drained soil. These are production-system-qualified traits, not interchangeable pH/temperature-only profiles.
- The maize sheet has blank texture/drainage fields. An empty category is unknown, not evidence that every soil is suitable.
- EcoCrop labels green gram as perennial; its crop-cycle range is 50-120 days. Preserve the source assertion and resolve production-cycle classification using Indian guidance. Pigeonpea, onion and cabbage also illustrate why biological lifespan and field occupancy must be distinct.
- EcoCrop reports rice cycles of 80-180 days and mango cycles of 150-365 days. The mango narrative describes several years to first bearing. Its cycle field must not become a 150-day orchard-establishment target.
- Legacy taxonomy matters: tomato is listed as *Lycopersicon esculentum*. Commercial strawberry `1112` is *Fragaria x ananassa*; NHB's legacy strawberry page names *F. vesca*. Several banana taxa/hybrids and sapota synonyms exist. Do not collapse them without an explicit mapping.

### 3.4 Indian conditions that require additional inputs

The reviewed NHB references are useful but dated; they include older statistics and broad cultivar assumptions. Import relevant condition facts with publication context, not their projected project economics or obsolete plant-protection prescriptions.

| Reviewed Indian reference | Source-specific conditions | Required feature consequence |
| --- | --- | --- |
| [Banana][nhb-banana] | 15-35 C, RH 75-85%, preferred pH 6.5-7.5, deep/well-drained loam; chilling below 12 C. Its rain discussion includes a June-September support period. | Preserve humidity, soil depth/drainage, low-temperature exposure and the correct rain period. The cited wind-damage threshold concerns strong winds; NASA daily mean wind cannot substitute for gust observations. |
| [Mango][nhb-mango] | pH 5.5-7.5; 750-3,750 mm annual rain; deep, well-drained soil; a dry period before flowering and rain/wind during flowering/fruiting matter. | Add actual or declared phenological windows and water/drainage inputs. Do not average this rainfall range with EcoCrop's different reference range. |
| [Apple][nhb-apple] | A Himalayan profile lists pH 5.5-6.5, 1,500-2,700 m altitude and 1,000-1,500 winter chilling hours at/below 7 C. The page also discusses low-chill cultivars. | Require cultivar and hourly winter temperatures for that chilling definition. EcoCrop's generic altitude maximum differs; do not automatically exclude valid Indian hill locations or apply high-chill requirements to every cultivar. |
| [Strawberry][nhb-strawberry] | pH 5.7-6.5; cultivar-dependent daylength/temperature response, including a short-day profile of at most 12 hours. | Calculate daylength from real latitude/date; record cultivar and production system. Resolve the source's taxonomic scope before attaching these traits to commercial strawberry outcomes. |
| [Tomato leaflet][nhb-tomato] | Indexed text describes pH 6.0-7.0, 21-24 C for fruit colour/quality and adverse fruit set above 32 C. | Stage-specific heat exposure is not a whole-life optimum. The PDF was reachable, but local text extraction and complete condition-table verification remain an import task; do not mark those values normalized/training-ready yet. |

Conflicts remain separate source assertions with geography, cultivar, stage and system qualifiers. A missing or conflicting mandatory requirement yields a limitation/withholding reason, not an invented average. This is a semantic-data requirement, not a new scientific-approval gate.

## 4. Requirement-to-feature crosswalk

Every admitted crop gets a machine-readable `requirement -> feature -> source -> unit -> time/depth support -> missing-data action` mapping. A requirement must not silently disappear because its acquisition is difficult.

**Status key:** existing means reusable in the current pilot, not already validated across India; planned means new extraction/derivation is needed; access-gated means its real acquisition must first be demonstrated.

| Requirement/input | Planned feature representation and temporal support | Route and current status |
| --- | --- | --- |
| Growing-season temperature | Mean daily minimum/maximum and mean temperature over the declared matching window; separate observed extremes, variability and source-qualified heat/frost exposure | NASA POWER `T2M`, `T2M_MIN`, `T2M_MAX`: existing daily route/summaries; crop-stage matching planned. Do not treat an EcoCrop absolute range as a universal daily injury threshold. |
| Annual rain/water and seasonal moisture supply | Separate full-year rainfall, requested-season rainfall, dry spells and wet days; separate documented supplemental-water depth/volume for the same support | `PRECTOTCORR`: existing. Annual requirements need an annual support; farmer irrigation/other water planned. Do not add groundwater storage or soil moisture to rainfall as if they were supplied irrigation. |
| Humidity | RH summaries/exposure over the same analysis or explicitly declared stage window | `RH2M`: existing. Stage/cultivar-specific requirements planned. |
| Light and radiation | Source-unit-normalized solar radiation; keep qualitative light/shade requirements distinct unless a documented mapping exists | `ALLSKY_SFC_SW_DWN`: existing acquisition. Quantitative radiation is not automatically an EcoCrop light-intensity category. |
| Photoperiod | Daylength hours from authentic latitude and date, summarized for the relevant growing window | Deterministic calculation planned; not inferred from cloudy-sky solar radiation. |
| Soil pH | pH with sample date, method, depth interval, spatial support and uncertainty where supplied | Dated laboratory input planned; SoilGrids alternative delivery access-gated. Soil pH in water and in a salt solution are not interchangeable without a documented conversion. |
| Texture, depth and rooting limits | Sand/silt/clay or a documented texture class; effective depth and restrictions with source/depth support | SoilGrids texture candidate; actual soil-profile/lab/farmer data for effective depth. Soil layer coverage is not itself an effective-rooting-depth measurement. |
| Drainage and waterlogging | Recorded drainage class, flood/standing-water duration and production system | Field/soil survey or appropriate water observations planned. Slope and soil moisture alone do not establish a categorical drainage class. |
| Salinity and fertility | EC in dS/m with measurement basis/depth; measured available nutrients, SOC and other supported properties separately | Mainly real soil/lab records, planned. Total nitrogen is not available N; generic EcoCrop fertility is not a numeric NPK requirement. |
| Altitude, terrain and erosion context | Elevation in metres, slope and documented terrain derivatives at native spatial support | NASA elevation/source terrain ingestion planned. Terrain is versioned static context, not a yearly soil-health measurement. |
| Current soil moisture | Quality-screened surface/root-zone observations with actual acquisition dates and native support | SMAP or actual sensors, access-gated. Surface and root-zone products remain distinct. |
| ET and water balance | ET/ET0 with method, input lineage, units and matching window; incomplete inputs leave the indicator unavailable | ECOSTRESS or defensible calculation from complete real inputs, planned/access-gated. Reference ET, actual ET and irrigation demand are different quantities. |
| Vegetation/bare-field history | Quality/cloud-screened vegetation indices and bare-period measures before cutoff, with observed-date coverage | Landsat/MODIS or other documented products, access-gated. Do not interpolate cloud gaps into observations or use the candidate crop's later growth as a preplant input. |
| Chilling and frost-sensitive fruit | Cultivar-specific winter chilling from adequate hourly data; separately defined frost exposure | Actual hourly station/reanalysis data, access-gated. Daily minimum/maximum cannot be expanded into fabricated hourly records. |
| Wind damage risk | Mean wind for descriptive climate; gust/max wind only from a compatible observed product | NASA `WS2M` daily mean existing; gust/storm exposure access-gated. Keep units and averaging periods explicit. |
| Growing duration and available field days | Source-qualified maturity/harvest window, regional sowing window, farmer availability interval and intended use | EcoCrop/official Indian calendars/farmer input, planned. Typical duration is not the realized harvest duration of a held-out crop. |
| Prior crops and rotation response | Actual previous crop(s), dates, field identity, residue/management context and measured before/after outcomes | VDSA or licensed longitudinal Indian trials/farmer histories, access-gated. Consecutive district crop totals are not a field sequence. |
| Management and farmer constraints | Irrigation access, recorded pre-decision plans, equipment/market exclusions and farmer priority weights | Actual dated farmer records and experiments, planned. Future realized fertilizer, irrigation and harvested area cannot be preplant predictors. No invented profit targets. |
| Perennial context | Establishment date/age, cultivar, bearing status, pruning/ratoon/flowering stage and commitment horizon | Orchard/plantation records and crop guidance, planned. Unknown age/phenology blocks the corresponding orchard-specific claim. |

The practical first cohort uses the existing seven daily weather variables plus genuine calendar/crop context and whatever compatible soil/terrain inputs are actually acquired. Expand with independent information, not every correlated raster available. Report the full planned crosswalk and its missing axes; a weather-only model must be labelled weather-only, not a complete soil/rotation assessment.

Train-only feature selection removes duplicate aliases, constant/all-missing columns and deterministic duplicates such as rainfall total plus its mean over the same complete fixed-length window. Correlation alone does not make two measurements identical. Use validation ablations to choose among overlapping providers or summaries. Keep provenance/coverage/quality metadata without counting it as extra agronomic information; missingness masks may be model inputs only with a recorded policy.

## 5. Time and spatial contract

### 5.1 Time fields and prediction modes

Persist `analysis_start`, `analysis_end`, `decision_cutoff`, intended `planting_window`, `growing_window`, source observation/support interval, `available_at`, `retrieved_at`, source version, crop stage and any separate `reference_window`.

The default is one explicitly requested analysis interval: **all time-varying observational features use that interval**. The current UK 30/90/365-day defaults must not silently widen an Indian user's shorter request. If a longer annual or historical reference is needed, expose it as an additional declared input; otherwise leave that comparison unavailable.

Distinguish these modes in every dataset and response:

| Mode | Permitted interpretation |
| --- | --- |
| Historical window analysis | Describes known conditions in a stated past period. It is not evidence that those data were available before that crop was planted. |
| Retrospective preplant experiment | Uses preplant observation support but may use later-released archives or a sourced calendar proxy. Publication/decision limitations remain explicit; no operational-backtest claim. |
| Strict as-of recommendation/backtest | Every predictive observation and reference release must be demonstrably available at/before the decision cutoff. Forecasts must have an archived issue time at/before cutoff and the correct valid window. Unknown availability is ineligible for this mode. |

Required rules:

1. Never use realized post-sowing weather, final management, final harvested area or the held-out harvest outcome as preplant inputs. A future intended crop horizon is not permission to look up its realized weather.
2. Same-season climatology uses preceding years only, with its exact support recorded separately. Modern normals cannot be silently attached to earlier decisions. Without an adequate declared climate/forecast reference, do not claim to know future growing conditions.
3. Preserve Kharif/Rabi/Zaid and provider-specific season definitions, agricultural-year labels and cross-calendar-year boundaries. District crop/season/year statistics without sowing dates remain season-level. Sourced calendar windows are proxies, not observed farmer planting/decision dates.
4. Rainfall totals and dry-spell counts need the required daily coverage; missing rain is not zero. Do not scale an incomplete sample into an invented full-year observation.
5. Soil tests retain sampling date, method and depth. Modern SoilGrids pH/SOC cannot be relabelled as historical measurements. Static/reference use and sample age must be visible; transformations need authentic inputs.
6. Crop traits and terrain are versioned reference context, not fake dated observations. Unknown historical reference availability prevents a strict as-of claim, not an honest retrospective study.
7. GAEZ v5 uses a 2020 baseline with 2019-2021 agricultural statistics; its AgERA5 climate periods include **1981-2000 and 2001-2020**. Future periods include **2021-2040, 2041-2060, 2061-2080 and 2081-2100**. Keep normals, projections, scenarios and water/input regimes separate. Never label a 20-year layer as a crop-season measurement.
8. Perennial predictions distinguish establishment from mature bearing, winter chilling from growing-season heat, and flowering from fruiting. A mango fruiting cycle is not time from seed to first harvest.

### 5.2 Spatial and identity rules

Use actual field boundaries or documented administrative geometries, recording CRS, geometry version, native product resolution, pixel/station selection, aggregation and coverage. District outcomes require district-supported weather/soil summaries; assigning a centroid's conditions to every farm creates false field precision.

Use area-weighted aggregation or an explicitly justified station/grid method. Do not pretend resampling a coarse climate raster produces new fine-scale observations. Crop masks must be dated and available for the prediction mode; a later crop map cannot locate an earlier season's planted crop for a preplant feature.

Preserve district boundary vintages and source crosswalks. ICRISAT DLD's apportioned historical/current-boundary products are not interchangeable, and DLD is not VDSA plot microdata. Splitting or apportioning agricultural totals requires an authentic documented method; no equal invented allocations.

## 6. Nonredundant storage and model-ready format

Reuse existing raw-asset handling, canonical identities, PostgreSQL/PostGIS, versioned dataset membership, Parquet exports and checksum verification. Extend the domain schema rather than create a parallel CSV-only pipeline or duplicate weather for every crop.

| Logical table/artifact | Required contents and invariant |
| --- | --- |
| Raw assets and request receipts | Immutable provider bytes, hash, request/retrieval metadata and access result. Identical bytes share storage; separate requests/revisions keep their own evidence. |
| Crop registry and source crosswalk | Canonical crop/use ID, source code/name, taxonomic or commodity-group scope, aliases, cultivar/system when known and yield/product basis. A source aggregate cannot generate child-species observations. |
| Crop requirement assertions | Crop, metric, optimal/absolute bounds or category, unit, stage, time/depth support, geography/system/cultivar qualifiers, source version and raw reference. Conflicting assertions remain separate. |
| Spatial supports and calendars | Field/district/grid identity, geometry/boundary version and real region/crop season windows; no invented field IDs behind regional labels. |
| Environmental observations | One canonical variable/support/time/depth/product record with quality/missingness state, units and lineage. Features reference these rows rather than copy them into each crop record. |
| Outcome observations | Genuine crop/season/year or field/cycle outcomes, source units, reporting/estimate flags, production/area basis, release/availability and evidence type. Keep field measurements, statistics and modelled reference targets separate. |
| Decision contexts and feature views | Typed intervals, support, candidate/task definition, derivation version and input references; a reproducible joined view for training/inference. |
| Dataset/split/model manifests | Immutable row IDs, eligibility/withholding reasons, crop vocabulary, split groups, feature schema, code/config/source hashes, transformations, training settings and artifact hashes. |

Keep missing, zero, not applicable, censored and unavailable distinct. Preserve lexical placeholders such as `no input`, blanks and `-` before normalization; they are not numeric zero. Neural models use explicit masks/learned missing representations. Computational padding must never become a stored environmental observation or counted valid day.

Convert units only from the actual source declaration. The reviewed FAOSTAT metadata uses **hg/ha** for yield; other files may differ. NHB tables can report area/production in thousands and flowers in counts; coconut or other commodities may also use non-mass quantities. Do not apply one universal tonnes-to-kg rule. Derive production/area only when units, harvested/sown-area definitions, scope and period match; retain reported yield and discrepancies.

Use existing evidence types (`published_parameter`, `published_recommendation`, `modelled_product`, `reanalysis`, `measured`, `surveyed`, `derived`, etc.) plus appropriate reporting flags, not an ambiguous `real=true`. Official aggregate estimates are authentic statistics, not individual field measurements. Provider-imputed values must not enter an "observed only" evaluation cohort.

Dataset exports should contain normalized Parquet tables and small JSON schema/manifest files, not repeated copies of complete source tables. Training-ready status is task-specific; usable weather does not establish available rotation labels.

## 7. Training targets and the meaning of softmax

| Cohort/task | How the sources are used | What the result can establish |
| --- | --- | --- |
| Crop-trait reference | EcoCrop plus qualified Indian guidance supplies crop descriptors/constraints to models | A reusable crop representation. Parameter ranges alone do not supply supervised environmental examples or prove which crop is best. Do not manufacture random points inside those ranges. |
| Indian reference suitability | Crop-specific GAEZ targets with matching native support, climate period and scenario; EcoCrop traits may be inputs | Ability to reproduce a published suitability product in held-out spatial blocks. This is explicitly model-product distillation, not independent farm validation. |
| Indian regional outcomes | DES/UPAg/NHB outcomes, compatible historical environment and crop/calendar context; FAOSTAT mainly for QA | Expected outcome of a named crop at the supported regional scale, with uncertainty. Crops historically selected were not necessarily optimal, and unplanted alternatives have no observed counterfactual yield. |
| Field/rotation outcomes | Real VDSA/Indian trial or farmer sequences with dated management and measured outcomes | Conditional field outcomes and, when data support it, effects associated with actual sequences. Regional crop totals cannot establish soil-health transitions or causal rotation benefits. |

For an eligible set of **trained, supported** crops `C`, a candidate score can produce:

```text
p(c | context, C) = exp((score_c - max_score) / T)
                    / sum_j exp((score_j - max_score) / T)
```

Use a positive temperature `T`, stable computation, explicit eligibility masks and the same task/horizon for all candidates. Ineligible classes have zero mass; an empty eligible set returns abstention, not uniform fallback probabilities. Return the actual candidate set because removing candidates changes the denominator.

Reject non-finite scores rather than publishing invalid probabilities. With one eligible candidate, its softmax value is 1 only because no alternatives remain; this is not 100% agronomic confidence.

**Interpretation:** this is a relative preference distribution under a defined scoring target. Several crops may grow well together; softmax does not give their independent probabilities of agronomic success. Independent suitability/success probabilities would require appropriately labelled per-crop outcomes and a separate sigmoid/multilabel formulation.

Do not train historical planted-crop classification and rename it "best crop." Do not feed raw cross-crop yields directly into softmax: forage mass, fresh vegetables and dry grain are incomparable. Crop-normalized outcome scores are also a declared comparison policy, not automatically economic or agronomic utility.

For the first softmax experiment, use a **reference-suitability head only after comparable GAEZ crop targets are acquired**. If GAEZ acquisition is blocked, proceed with conditional outcome regressors and report that a defensible crop-preference target is still missing. Do not invent one to satisfy the requested output shape.

Later outcome-informed rankings need an explicit objective, such as crop-specific performance relative to training-only reference distributions, and documented farmer constraints. Water, soil-health or market priorities may affect ranking only through available evidence and declared policy; no invented nitrogen bonuses, profit labels or causal guarantees.

Temperature fitting against a reference product measures reference alignment, not farmer-success calibration. Only use classification calibration metrics when genuine labels with that probability meaning exist.

## 8. Architectures to compare

All competitors for a task use the same eligible examples, crop vocabulary, information cutoff and evaluation partitions. Sequence models may consume the underlying daily observations used by tabular summaries; record that representation difference and compare ablations.

| Candidate | Proposed starting architecture | Why/when to run it |
| --- | --- | --- |
| B0: non-neural baseline | Training-only per-crop/context reference, plus a regularized linear/logistic or simple ranking baseline when appropriate for the target | Establish whether complexity helps. A crop median is an outcome baseline, not a best-crop engine. |
| B1: CatBoost | Conditional crop scorer/regressor with crop/context categories, real weather summaries and available static features; separate task heads/models as needed | First serious model: good fit for moderate heterogeneous tabular data and missing values; reuses current experience. A softmax may wrap compatible candidate scores, or a native multiclass head may be used only for a legitimate categorical target. |
| B2: embedding MLP | Crop/categorical embeddings plus scaled numeric features and masks; initially two or three hidden layers of roughly 128-256 units, regularization and early stopping | Small, inexpensive neural comparator. Combine crop traits and context without requiring a huge network. |
| B3: FT-Transformer | Small feature-token encoder, initially two to four blocks and roughly 64-128 embedding width; crop-conditioned output head | Tests nonlinear feature interactions if the independent training sample count justifies it. Not automatically better than CatBoost. |
| B4: temporal hybrid | Small TCN **or** GRU over dated weather/masks, with a soil/terrain/crop-trait branch and task-specific head | Tests whether dry spells, transitions and daily sequences add value beyond summaries. Needs genuine daily coverage and a fixed declared time contract. Do not run both variants initially without evidence of benefit. |
| B5: two-tower scorer | Environment/time encoder and crop-trait encoder, initially about 64-dimensional representations, with a learned interaction/ranking head | Useful when many crops have comparable reference targets. A real prior-crop sequence branch can be added later. Architectural ability to encode a new crop does not authorize unseen-crop testing or recommendations. |
| Ensemble, conditional | Validation-selected blend of the strongest compatible models; recalibrate using only the calibration partition | Only if it improves the same task on the same crop set/cohort. Do not average GAEZ-reference probabilities, regional yield predictions and orchard/annual outputs together. |

For continuous outcomes compare appropriate regression losses and uncertainty methods; for comparable scored candidate lists compare ranking/distribution losses; for genuine categorical labels compare cross-entropy. An output head does not change the evidence required for its target.

Suggested experiment order: B0/B1, B2, then B4 if daily temporal structure is supported; B3/B5 are additional competitors once the corpus is large/diverse enough. Keep one narrow, predeclared search budget per architecture. An LLM or very large pretrained model is not necessary for this structured-data task.

Use feature-group ablations: weather/calendar, plus soil/terrain, plus crop traits, then genuine management/history. Keep the evaluated cohort fixed when attributing improvement to a feature; also report how stricter availability changes overall coverage. Fit scaling, feature selection, target normalization and class weights on training data only. No duplicate-row oversampling or synthetic weather augmentation.

## 9. RAM/VRAM-aware experiment scheduling

Observed at **2026-11-15 05:36:38 -08:00**:

| Resource | Observed capacity/availability |
| --- | --- |
| RAM | 31.15 GiB total; 12.18 GiB free |
| CPU | 16 logical processors |
| GPU | NVIDIA GeForce RTX 4080 SUPER |
| VRAM | 16,376 MiB total; 13,175 MiB free, approximately 12.87 GiB |

This is a shared-machine snapshot, **not an allocation or a promise that those resources remain free**. Scheduling is proposed here, not yet implemented.

Before every run, remeasure free RAM/VRAM and profile a bounded real-data batch. Reserve at least **6 GiB RAM and 3 GiB VRAM** for other activity; require an additional 25% margin over the measured incremental peak, including outstanding growth of already admitted jobs.

At the snapshot, this leaves about 6.18 GiB RAM and 9.87 GiB VRAM before that margin, or about 4.94 GiB / 7.90 GiB of newly admitted peak demand if no other owned job has outstanding growth. Recompute instead of hardcoding these budgets.

Default to one GPU training job, CPU thread limits around two and no extra data-loader workers initially. A small CPU competitor may run alongside it only if combined measured demand fits. Multiple models can be trained sequentially; concurrency is not a quality requirement.

Reduce batch size, use column-pruned/chunked Parquet loading and queue jobs when resources are tight. Account for data copies, activations, optimizer state, temporary arrays and checkpoints, not parameter count alone. Mixed precision is optional and must preserve numerical behavior. Record peak RAM/VRAM, runtime and model size for each experiment.

Do not materialize an India-wide crop/scenario Cartesian product in RAM. Store shared environmental features once and stream only source-supported candidate/target pairs; absent crop outcomes must not be filled to complete a matrix.

Only pause/stop owned processes. Never replace the shared Python environment, stop the shared database or kill another session's GPU job to make room. Keep the existing separate ML environment; install new optional dependencies only as their architecture is implemented.

## 10. Cross-validation, held-out testing and saved evidence

### 10.1 Non-negotiable crop coverage

For **every** fold and every final train/tuning/calibration/test split:

```text
validation_crop_classes UNION calibration_crop_classes UNION test_crop_classes
    MUST BE A SUBSET OF training_crop_classes
```

Require actual target-bearing training examples for each admitted class, not just a trait lookup or a label-encoder entry. Fit the vocabulary on the training partition. An unsupported crop is withheld before fitting/evaluation, with a reason; never move a later test observation into training to satisfy coverage.

The two-tower/trait model must obey the same rule. New crops can enter the registry, but they need new training support and a new model version before model-based evaluation or recommendations.

### 10.2 Split design

Choose partitions from the acquired date/group coverage before model fitting, not by looking for a favorable score. Use rolling-origin development folds where history allows, a separate calibration partition, and a locked final test. Reserve whole harvest/availability periods; enforce that training labels were available before a strict as-of evaluation decision.

Group authentic repeats together: field/household/study or treatment unit for trials; district/boundary lineage for regional outcomes; native spatial blocks and scenario/product siblings for GAEZ. Never split the same grid cell's alternative crops or revisions across train and test.

For regional outcomes report temporal generalization and spatial generalization separately, plus a joint held-out cohort when feasible. Crop classes must remain covered in each case. Spatial group identifiers are not substitutes for environmental features; an unseen geography is not an unseen crop. Record the supported geographic domain.

Predeclare minimum independent spatial groups and seasons per crop after the first coverage audit, before evaluating the locked test. Report counts by crop, year, region, production system and evidence type; thousands of correlated pixels are not thousands of independent farms. Sparse crops stay in intake rather than being padded or artificially balanced.

Preprocessing, feature selection, normalizers, hyperparameters and model selection use training/development partitions only. Calibration uses its reserved partition. Open the final test once for the frozen comparison; later changes require a newly versioned evaluation protocol rather than repeated test-driven tuning.

### 10.3 Metrics and selection

| Task | Required comparison |
| --- | --- |
| Reference suitability | MAE/appropriate ordinal error for reference scores; NDCG or other justified ranking agreement on comparable candidate sets; crop/region coverage. State that labels originate from GAEZ. |
| Conditional crop outcomes | MAE/RMSE in the actual crop/product unit; crop-normalized comparison and macro-averaged skill versus B0; uncertainty interval coverage/width where supported. No raw-yield winner across incompatible crops. |
| Genuine categorical/multilabel task, if acquired | Log loss, Brier score and calibration diagnostics with their true event meaning; macro/per-crop results and class support. Top-k accuracy alone is insufficient. |
| Rotation/field task, if acquired | Held-out field/sequence outcomes and measured soil/water responses, preserving intervention/selection limitations; compare with observed current rotations where available. |
| All tasks | Region/season/crop/system breakdown, abstention and missing-input coverage, peak memory, latency, artifact size and stability across supported development folds. |

Choose champions on development evidence and resource cost; show failures and baseline wins. Do not report a model as best because it won only the final test or because its softmax confidence is high.

### 10.4 Persistent artifacts

Preserve raw bytes and source receipts; normalized observations/traits; source and licence manifests; temporal/spatial joins; feature lineage; eligibility/withheld IDs; complete split memberships; crop vocabulary; model configuration and seed; dependency/code hashes; fitted transformations; checkpoints; calibration objects; per-example validation/test predictions; metrics by group; resource telemetry; and clean-process reload results.

Keep predictions linked to the original source outcome and its unit/basis. Save the locked test bundle before tuning, not after selecting a winner. Store restricted records only in authorized local storage; Git contains code/configuration/documentation, not secrets or private microdata.

The planning audit is already saved under:

```text
data\raw\india-source-review-4ea3341a2e8e4342b62b111e3cc9dd69\
    ecocrop-catalogue.json
    ecocrop-<source-id>.profile.json
    <content-sha256>
    <request-id>.request.json
```

The profile JSON files are explicitly marked **lexical extraction for planning, not model training**. Their tables retain source headings, optimal/absolute ordering and blanks. They need the typed normalizer and semantic checks above; they are not already a training/test split.

## 11. Implementation sequence and hard exit cases

This is the AI work sequence, not a replacement for the original data-platform S01-S11 sequence. Production source/domain completion still follows the owning platform contracts. A passing experiment does not mark the full inventory complete.

| Increment | Work | Hard exit before the next dependent increment |
| --- | --- | --- |
| I01: registry and requirements | Add versioned Indian crop/use mappings, source assertions and a typed EcoCrop/Indian-reference normalizer using the archived samples | Independently checked authentic values, explicit conflict/missing states, real PostgreSQL/export roundtrip and repeat-import safety. No inferred Indian presence from the global list. |
| I02: Indian outcome/calendar intake | Acquire authorized DES/UPAg/NHB and, where available, VDSA/experiment data; pin calendar/boundary/product units | At least one real export parsed and reconciled per enabled source; observed/statistical/modelled roles separated; crop-season coverage report and access blockers saved. |
| I03: matched environment | Reuse NASA acquisition; add only verified soil/terrain/hourly/satellite routes needed by the chosen cohort | Indian spatial support and declared time windows verified; source outages, incomplete intervals and unresolved units fail visibly without fallback values. |
| I04: dataset and split builder | Join canonical references into task-specific Parquet views; implement eligibility, as-of policies, crop vocabulary and grouped temporal splits | No duplicate logical examples, no future/unsupported references, all held-out crops present in training, and independently reproducible IDs/hashes. Save the locked test before tuning. |
| I05: baselines and CatBoost | Implement B0/B1 against each viable target with profiled resource admission | Targeted real-data training and hard held-out development cases, baseline comparison, artifact reload and unit/crop-compatible predictions. No false softmax target if GAEZ/choice evidence is missing. |
| I06: neural competitors | Add B2, then eligible B4/B3/B5 in small separate increments | Same cohorts/cutoffs/splits, missing-mask correctness, finite loss/output, measured peak memory within admission budget and reload parity. Each architecture must justify its cost. |
| I07: frozen comparison/calibration | Select on development results, fit valid calibration, optionally ensemble compatible models, evaluate locked test | Per-crop/region/time reports, probability semantics, abstention and all saved predictions; no unseen-crop evaluation or repeated test-guided tuning. |
| I08: serving handoff | Define versioned inference input/output and integrate with the separately owned backend API work | Correct model/task/vocabulary chosen; windows and supports returned; missing/unsupported inputs rejected or explicitly qualified; real saved-example replay from a clean process. Do not claim an HTTP route exists before implementation. |
| I09: real rotation extension | Acquire field sequences and measured transitions; extend the relevant model with history and farmer constraints | Demonstrate sequence evidence rather than district pseudohistories. Compare the existing rotation and at least two supported alternatives when evidence permits; otherwise report insufficient supported alternatives. |
| I10: broader crop families | Expand vegetables, orchards, plantation/forage tasks as their own data/targets become viable | Every new crop has real training support, time/system-compatible conditions and a new held-out protocol. Perennial predictions require the additional horizon/age/phenology inputs. |

I01 and I02 can proceed independently; I03 depends on the acquired cohort's locations/windows. I04 depends on I01-I03. I05 precedes I06-I07; I08 needs the selected model and inference contract. I09 requires genuine sequence data regardless of earlier regional-model success. I10 reuses the earlier data/model gates for each new family.

Hard regression cases should use authentic archived records or deterministic checks against them, not fabricated agricultural fixtures:

- Reimport the same source/revision and verify canonical counts stay stable while provenance remains intact.
- Replay a genuine record outside the declared cutoff/window and ensure it cannot enter an as-of feature view; distinguish retrieval time from availability time.
- Attempt an annual-requirement comparison with a shorter authentic rain series; report incompatible temporal support instead of scaling it up.
- Reject a GAEZ-normal/season or modern-soil/historical-measurement join that falsely relabels support.
- Use the real mustard aggregate, banana/strawberry aliases and conflicting apple/mango reference scopes to check that identities and assertions are not silently merged.
- Validate a split manifest missing a genuine crop from training and stop **before** evaluation; record the unsupported crop instead of producing a score.
- Demonstrate separate grain/forage/fresh-product targets, genuine missing weather behavior and no post-harvest feature leakage.
- Verify masked softmax, empty-candidate abstention and model reload using authentic eligible/withheld contexts; no fallback farm or fabricated class record.
- Exercise resource admission against measured machine telemetry without starting a job that exceeds the shared-machine reserve.

Commit each coherent implementation increment on `backend-ai` after its relevant hard case and regression checks pass. Keep documentation/source-audit commits separate from adapter/model changes. Preserve unrelated work and the existing UK artifacts; do not bundle an unfinished architecture into a successful data-ingestion commit.

## 12. Current completion and next implementation decision

Completed for this planning task: review of all seven requested source families, additional Indian horticulture/calendar/soil routes, a broader staged crop catalogue, 25 archived EcoCrop condition profiles, the feature/time/storage contracts, competing architectures, resource policy and held-out evaluation design.

**Not completed:** Indian APY/NHB/VDSA outcome ingestion, India-wide crop-presence verification, production requirement normalizers, GAEZ Indian raster acquisition, new feature adapters, Indian training/evaluation, resource scheduling or a field-rotation API. Those are implementation gates above, not implied by this document.

Recommended next implementation: I01/I02, followed by a real coverage audit to freeze the first task/vocabulary. Train B0/B1/B2 on the same viable corpus before spending resources on additional architectures. Keep all 12 initial reporting groups in intake, but activate only supported classes; expand horticulture from evidence rather than promising every listed crop on day one.

## Sources

Primary sources are linked where their findings are used above; the condition table links directly to each sampled EcoCrop sheet. A source link does not imply that every downloadable product has passed acquisition or normalization.

[eco]: https://data.apps.fao.org/catalog/dataset/ecocrop
[eco-home]: https://ecocrop.apps.fao.org/ecocrop/srv/en/home
[eco-temp]: https://ecocrop.apps.fao.org/ecocrop/srv/en/helpShow?id=2000
[eco-rain]: https://ecocrop.apps.fao.org/ecocrop/srv/en/helpShow?id=2001
[gaez]: https://www.fao.org/gaez/en/
[dssat]: https://dssat.net/about/
[apsim]: https://docs.apsim.info/docs/
[vdsa]: https://vdsa.icrisat.org/vdsa-database.aspx
[faostat]: https://data.fao.org/catalog/dataset/d24a448b-3b62-4c09-8c1d-4a39bb599876
[des]: https://data.desagri.gov.in/website/crops-apy-report-web
[upag]: https://upag.gov.in/dash-reports/desdistrictwisecompletedatasetreport
[calendar]: https://upag.gov.in/national-calendar
[nhb]: https://www.nhb.gov.in/model-project-reports/index.html
[nhb-stats]: https://nhb.gov.in/area-pro/FinalEstimates.xls
[nhb-banana]: https://www.nhb.gov.in/model-project-reports/Horticulture%20Crops/banana/Banana1.htm
[nhb-mango]: https://www.nhb.gov.in/model-project-reports/Horticulture%20Crops/Mango/Mango1.htm
[nhb-apple]: https://www.nhb.gov.in/model-project-reports/Horticulture%20Crops/apple/apple1.htm
[nhb-strawberry]: https://www.nhb.gov.in/model-project-reports/Horticulture%20Crops/Strawberry/Strawberry1.htm
[nhb-tomato]: https://nhb.gov.in/pdf/vegetable/tomato/tom012.pdf
[power]: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
[soilgrids]: https://docs.isric.org/globaldata/soilgrids/index.html
