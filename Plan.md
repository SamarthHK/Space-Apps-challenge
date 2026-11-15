Build this in the branch backend:
# **Complete Agriculture Data Collection & Processing Plan**

Technical project specification · Notebook-first development · Local geospatial data platform

The objective is to build a system that accepts a KML file containing one or more agricultural plots, identifies the geographical area, retrieves all available environmental and agricultural information for that area, processes it, and stores it locally in a structured database.

The system will eventually support crop suitability analysis, crop-growth prediction and multi-season crop-rotation optimization.

I recommend developing this as a Python geospatial data platform with **Jupyter notebooks as the initial development and documentation interface**, followed by a reusable Python package once the notebooks have been validated.

This specification covers the full scope we've discussed, including:

- All environmental characteristics.
- Crop-specific requirements.
- Germination and establishment.
- Crop development and growth.
- Historical crop performance.
- Biological risks.
- Crop rotation and soil interactions.
- Cultivation and management.
- Sensors, APIs, downloadable datasets and field measurements.
- KML-based geographical extraction.
- Local database design, file storage and processing.
- Notebook development and subsequent Python implementation.

One important boundary: economics, crop prices, market demand, profitability and input costs are reserved for a later project phase, as previously planned.

## **1. Overall system architecture**

The system should have five main layers.

**1. Geographical input**

## **KML / KMZ**

Farm boundaries, multiple plots, region polygons

**2. Geospatial processing**

Parse polygons · Validate geometry · Calculate area · Determine data coverage · Intersect source datasets

**3. Data acquisition pipelines**

Soil

Climate

Water

Land history

Crop requirements

Crop development

Crop performance

Biological risks

Rotation effects

Management

**4. Local data storage**

PostgreSQL/PostGIS + GeoTIFF + NetCDF + Parquet + JSON

**5. Agricultural analysis**

Environmental profiles · Crop suitability · Crop growth · Rotation modelling

The architecture needs to separate three things:

1. **Raw data:** exactly what an external source returned or what was downloaded.
2. **Processed data:** cleaned, converted and spatially extracted information.
3. **Agricultural interpretations:** indicators, estimates and crop-related conclusions derived from the processed data.

Never overwrite raw information with processed information. This is important when a newer dataset or improved processing method becomes available.

### **1.1 The ten data domains**

The seven logical databases from our previous plan can be expanded into ten data domains for implementation.

| Domain                              | Data                                                                 |
| ----------------------------------- | -------------------------------------------------------------------- |
| 1. Soil                             | Physical, chemical and biological soil properties                    |
| 2. Terrain and geology              | Elevation, slope, geological characteristics and hydrology           |
| 3. Climate                          | Rainfall, atmospheric conditions and climate extremes                |
| 4. Water                            | Groundwater, surface water, irrigation and soil moisture             |
| 5. Historical land                  | Land cover, vegetation, crop history and environmental changes       |
| 6. Crop requirements                | Conditions required by individual crops and cultivars                |
| 7. Crop development and performance | Germination, growth, yield and stress response                       |
| 8. Biological environment           | Pests, diseases, weeds and pollination                               |
| 9. Crop rotation                    | Nutrient cycling, residues, moisture carryover and crop interactions |
| 10. Cultivation management          | Seed, sowing, fertilizers, irrigation, tillage and harvesting        |

Domains 1–5 describe the geographical environment. Domains 6–10 describe crops, their biological behaviour and how humans cultivate them.

# **2. Complete master data inventory and acquisition sources**

The following is the unified inventory. I've consolidated repeated characteristics, such as soil pH appearing in several earlier lists, into a single canonical variable. Where a characteristic has several different meanings, such as soil moisture and irrigation water, those remain separate.

A source listed for a variable is a candidate acquisition source, not a guarantee that it supplies a public API or plot-level measurements. I distinguish direct measurement, satellite products, modelled datasets, research databases and manual collection.

## **2.1 Soil characteristics**

[Embedded Asset](https://images.openai.com/static-rsc-4/RmjEk5ynxcxQYBikHXEw4FUmOVqPCA9UIvDcxLetqMFQ3-aH_C8QKMl60K1CqXaNbfEh-t3nKld0tUFNT_LckhsX8KeBhlJiQaOrTm77LXH9VdUCOtQaih8Gp0YhyUsBlZ9enLmcoynL5jpH_s8Qdxv-PlEgznbveSwemRotyeQ?purpose=inline)

[simplyscapes.com](https://www.simplyscapes.com/learn/how-often-should-i-water-my-lawn-and-plants-a-straightforward-guide?utm_source=chatgpt.com)

Soil data should be stored with depth information. A soil measurement at 0–5 cm is not interchangeable with a measurement at 30–60 cm.

| Characteristic             | Data to collect                                         | Primary acquisition source                                                                   | Method                   |
| -------------------------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------ |
| Soil classification        | Soil order, subgroup and classification system          | NBSS&LUP, SoilGrids                                                                          | Soil maps / API          |
| Sand content               | Percentage of sand particles                            | SoilGrids                                                                                    | REST API / raster        |
| Silt content               | Percentage of silt particles                            | SoilGrids                                                                                    | REST API / raster        |
| Clay content               | Percentage of clay particles                            | SoilGrids                                                                                    | REST API / raster        |
| Soil texture class         | Sandy, silty, loamy, clayey and subclasses              | Derived from particle fractions; Soil Health Card                                            | Calculation / testing    |
| Soil pH                    | Acidity or alkalinity                                   | SoilGrids, Soil Health Card                                                                  | API / laboratory         |
| Electrical conductivity    | Soil salinity                                           | Soil Health Card, laboratory                                                                 | Laboratory               |
| Soil sodicity              | Exchangeable sodium, ESP and related indicators         | Soil laboratory, agricultural universities                                                   | Laboratory               |
| Organic carbon             | Soil organic carbon concentration                       | SoilGrids, Soil Health Card                                                                  | API / testing            |
| Organic matter             | Organic matter concentration                            | Soil laboratory, derived from organic carbon                                                 | Laboratory / calculation |
| Total nitrogen             | Total soil nitrogen                                     | SoilGrids, laboratory                                                                        | API / testing            |
| Available nitrogen         | Plant-available nitrogen                                | Soil Health Card, laboratory                                                                 | Laboratory               |
| Available phosphorus       | Extractable plant-available phosphorus                  | Soil Health Card, laboratory                                                                 | Laboratory               |
| Available potassium        | Extractable plant-available potassium                   | Soil Health Card, laboratory                                                                 | Laboratory               |
| Sulphur                    | Available sulphur                                       | Soil Health Card, laboratory                                                                 | Laboratory               |
| Micronutrients             | Zinc, iron, copper, manganese and boron                 | Soil Health Card, laboratory                                                                 | Laboratory               |
| Calcium carbonate          | CaCO₃ concentration                                     | Soil surveys, laboratory                                                                     | Map / testing            |
| Cation exchange capacity   | CEC                                                     | SoilGrids, laboratory                                                                        | API / testing            |
| Bulk density               | Dry soil mass per unit volume                           | SoilGrids, laboratory                                                                        | API / testing            |
| Soil porosity              | Total pore volume                                       | Derived from bulk density and particle density                                               | Calculation / testing    |
| Coarse fragments           | Gravel and rock fragment fraction                       | SoilGrids, soil survey                                                                       | API / map                |
| Total soil depth           | Depth to bedrock or restrictive layer                   | NBSS&LUP, field survey                                                                       | Maps / field             |
| Effective rooting depth    | Usable depth for crop roots                             | Soil survey, ICAR, field survey                                                              | Field assessment         |
| Drainage class             | Excess water removal characteristics                    | NBSS&LUP, soil surveys                                                                       | GIS / field              |
| Infiltration rate          | Water entry rate into soil                              | Field tests, agricultural research                                                           | Field sensor/test        |
| Hydraulic conductivity     | Water movement through soil                             | Laboratory, pedotransfer functions                                                           | Testing / model          |
| Field capacity             | Soil water content after gravitational drainage         | Laboratory, pedotransfer functions                                                           | Testing / model          |
| Permanent wilting point    | Soil water content at permanent wilting                 | Laboratory, pedotransfer functions                                                           | Testing / model          |
| Available water capacity   | Water between field capacity and wilting point          | Derived from soil hydraulic data                                                             | Calculation              |
| Soil water retention curve | Relationship between water content and matric potential | Laboratory, pedotransfer functions                                                           | Testing / model          |
| Soil contamination         | Heavy metals, pesticide residues and other contaminants | Pollution monitoring, laboratory                                                             | Laboratory               |
| Soil temperature           | Temperature at specified soil depths                    | SoilGrids-related products only where suitable; field sensors; ERA5-Land for gridded context | Sensor / model           |

**Main sources and access strategy**

- SoilGrids: `https://rest.isric.org/soilgrids/v2.0/` — use its property query interface and downloadable rasters. Candidate properties include `sand`, `silt`, `clay`, `phh2o`, `soc`, `nitrogen`, `bdod`, `cec` and `cfvo`.
- NBSS&LUP: soil surveys, classification and Indian soil maps. Investigate map/data access and institutional datasets.
- Soil Health Card: laboratory measurements, particularly EC, available NPK and micronutrients. Use farmer-supplied report imports or authorized datasets; do not assume an unrestricted API.
- Soil laboratories and agricultural universities: soil hydraulic characteristics, contaminants and detailed nutrient analysis.

**Important gaps:** SoilGrids should not be used to invent EC, plant-available phosphorus or potassium. We need actual testing or another explicit source. Likewise, estimated available water capacity must be labelled as a derived value.

## **2.2 Terrain, topography and geology**

[ArcGIS](https://images.openai.com/static-rsc-4/J8OZU335QWM-qNuCi_dHEbhBjsDeKPIlIhbthO4-ByFsb9L-0zYlIJjSzAYgv1tFHiupNjLFRVzH8K8qRWbXqUYYUtnzAHmwzjikmXzDyAiQZjS_otlFhbo5AeJxm3ZXLG5Fg5ezN2nJ-Z_TYosJr46dLZtI-6i2rUfsQddfsig?purpose=inline)

[arcgis.com](https://www.arcgis.com/home/item.html?id=2daafb35594241a7a474bbd941b205f8\&utm_source=chatgpt.com)

| Characteristic            | Data to collect                                         | Primary source             | Method               |
| ------------------------- | ------------------------------------------------------- | -------------------------- | -------------------- |
| Elevation                 | Metres above sea level                                  | Copernicus DEM, SRTM, ALOS | Raster               |
| Slope                     | Degrees or percentage                                   | Derived from DEM           | GIS calculation      |
| Aspect                    | Direction faced by slope                                | Derived from DEM           | GIS calculation      |
| Terrain curvature         | Profile and plan curvature                              | Derived from DEM           | GIS calculation      |
| Topographic wetness index | Relative water accumulation potential                   | Derived from DEM           | GIS calculation      |
| Flow accumulation         | Upstream contributing area                              | DEM, HydroSHEDS            | GIS calculation      |
| Drainage density          | Drainage length per unit area                           | HydroSHEDS, India-WRIS     | GIS calculation      |
| Geological formation      | Underlying geological unit                              | Geological Survey of India | GIS map              |
| Lithology                 | Rock and material type                                  | GSI                        | GIS map              |
| Geomorphology             | Landform and surface processes                          | Bhuvan, GSI                | GIS map              |
| Soil parent material      | Material from which soil developed                      | NBSS&LUP, GSI              | GIS map              |
| Watershed membership      | Catchment containing the plot                           | India-WRIS, HydroSHEDS     | Spatial intersection |
| Landform position         | Ridge, slope, valley, floodplain and similar categories | DEM, geomorphology maps    | Classification       |

Sources:

- Copernicus DEM: elevation.
- SRTM: elevation.
- ALOS: elevation products.
- HydroSHEDS: river networks, watersheds and drainage.
- Bhuvan and GSI: thematic and geological maps.

## **2.3 Rainfall and precipitation**

| Characteristic             | Data to collect                                         | Primary source                   | Method                  |
| -------------------------- | ------------------------------------------------------- | -------------------------------- | ----------------------- |
| Annual rainfall            | Total annual precipitation                              | IMD, KSNDMC, NASA POWER          | Station / API / raster  |
| Monthly rainfall           | Monthly precipitation                                   | IMD, CHIRPS, NASA POWER          | API / raster            |
| Daily rainfall             | Daily precipitation                                     | KSNDMC, IMD, NASA POWER          | Station / API           |
| Rainfall intensity         | Precipitation rate over shorter intervals               | Rain gauges, GPM IMERG           | Sensor / satellite      |
| Rainy days                 | Days above a defined rainfall threshold                 | Rainfall records                 | Derived                 |
| Growing-season rainfall    | Rainfall during crop-season dates                       | Rainfall records + crop calendar | Derived                 |
| Rainfall distribution      | Intra-seasonal distribution                             | Rainfall records                 | Derived                 |
| Monsoon onset              | Arrival date based on official definition               | IMD, KSNDMC                      | Official data / derived |
| Monsoon withdrawal         | Withdrawal date                                         | IMD                              | Official data           |
| Rainfall variability       | Interannual and seasonal variation                      | IMD, CHIRPS                      | Derived                 |
| Extreme rainfall frequency | Frequency of heavy rainfall events                      | IMD, GPM                         | Derived                 |
| Longest dry spell          | Maximum consecutive dry days                            | Daily precipitation              | Derived                 |
| Rainfall anomaly           | Deviation from historical normal                        | IMD, CHIRPS                      | Derived                 |
| SPI                        | Standardized precipitation index                        | CHIRPS, IMD, GPM                 | Derived                 |
| SPEI                       | Standardized precipitation and evaporative-demand index | CHIRPS + ET0/ETp                 | Derived                 |
| Long-term rainfall trends  | Multi-year or decadal change                            | IMD, CHIRPS, ERA5-Land           | Time-series analysis    |

**Acquisition sources**

- NASA POWER: `https://power.larc.nasa.gov/api/temporal/` — convenient daily and monthly point queries.
- KSNDMC: local weather station and rainfall observations; investigate station-data access or formal request.
- IMD: gridded and station meteorological data.
- CHIRPS: long-term gridded rainfall.
- GPM IMERG: high temporal-frequency satellite precipitation.

For the Karnataka pilot, prioritize KSNDMC and IMD for local reference observations, with NASA POWER and CHIRPS as gridded comparisons.

## **2.4 Atmospheric climate**

| Characteristic                   | Data to collect                                | Primary source                            | Method                            |
| -------------------------------- | ---------------------------------------------- | ----------------------------------------- | --------------------------------- |
| Average temperature              | Daily/monthly mean air temperature             | IMD, NASA POWER, ERA5-Land                | Station / API / reanalysis        |
| Maximum temperature              | Daily maximum temperature                      | IMD, NASA POWER                           | Station / API                     |
| Minimum temperature              | Daily minimum temperature                      | IMD, NASA POWER                           | Station / API                     |
| Diurnal temperature range        | Daily maximum minus minimum                    | Derived                                   | Calculation                       |
| Relative humidity                | Mean and maximum/minimum humidity              | IMD, NASA POWER, ERA5-Land                | Station / API                     |
| Dew point                        | Daily/monthly dew point                        | ERA5-Land                                 | Reanalysis                        |
| Vapour pressure deficit          | Atmospheric drying demand                      | Temperature + humidity                    | Derived                           |
| Wind speed                       | Mean and maximum wind speed                    | NASA POWER, ERA5-Land                     | API / reanalysis                  |
| Wind direction                   | Direction of wind                              | ERA5-Land, weather stations               | Reanalysis / station              |
| Atmospheric pressure             | Surface pressure                               | ERA5-Land                                 | Reanalysis                        |
| Solar radiation                  | Incoming shortwave solar energy                | NASA POWER, ERA5-Land                     | API / reanalysis                  |
| Net radiation                    | Net radiative energy                           | ERA5-Land, derived                        | Reanalysis / calculation          |
| Sunshine duration                | Daily hours of sunshine                        | IMD/weather station                       | Station                           |
| Cloud cover                      | Total cloud fraction                           | ERA5-Land                                 | Reanalysis                        |
| Heatwave frequency               | Events under a defined heatwave criterion      | IMD, weather stations                     | Derived / official classification |
| Cold spell frequency             | Unusually cold event count                     | IMD                                       | Derived                           |
| Frost occurrence                 | Freezing-temperature events                    | Weather stations, ERA5-Land               | Derived                           |
| Growing degree days              | Accumulated crop-available thermal time        | Temperature + crop base temperature       | Derived                           |
| Potential evapotranspiration     | Potential evaporative demand                   | ERA5-Land, TerraClimate                   | Dataset / model                   |
| Reference evapotranspiration ET0 | Standardized reference-crop water demand       | Weather variables, FAO-56 Penman–Monteith | Derived                           |
| Climate classification           | Arid, semi-arid, tropical, etc.                | WorldClim, Köppen-Geiger                  | Dataset                           |
| Aridity index                    | Precipitation relative to potential ET         | CHIRPS + ET dataset                       | Derived                           |
| Climate projections              | Future temperature and precipitation scenarios | CMIP6, WorldClim                          | Model dataset                     |

Sources:

- NASA POWER.
- IMD and KSNDMC.
- ERA5-Land.
- TerraClimate.
- WorldClim.
- CMIP6.

## **2.5 Water resources and availability**

| Characteristic                      | Data to collect                                         | Primary source                             | Method                 |
| ----------------------------------- | ------------------------------------------------------- | ------------------------------------------ | ---------------------- |
| Surface-water extent                | Geographic water-body extent                            | JRC Global Surface Water, Sentinel-2       | Satellite              |
| River network                       | River locations and connectivity                        | HydroSHEDS, India-WRIS                     | Vector dataset         |
| Reservoir storage                   | Total stored water                                      | India-WRIS, water authorities              | Portal / station       |
| Reservoir water level               | Water surface level                                     | Water authorities                          | Measurements           |
| Canal network                       | Canal location                                          | India-WRIS, irrigation departments         | GIS                    |
| Irrigation command area             | Land served by an irrigation scheme                     | India-WRIS, irrigation departments         | GIS                    |
| Surface runoff                      | Overland water flow                                     | ERA5-Land, hydrological models             | Model                  |
| Streamflow                          | River discharge                                         | Water authorities, hydrological models     | Station / model        |
| Flood extent                        | Extent of historical inundation                         | Sentinel-1, NRSC                           | Satellite              |
| Flood frequency                     | Repeated flooding history                               | Sentinel-1, historical flood maps          | Derived                |
| Groundwater level                   | Depth below ground level                                | CGWB, state groundwater departments        | Well observation       |
| Groundwater trends                  | Seasonal and long-term groundwater variation            | CGWB                                       | Time series            |
| Aquifer type                        | Water-bearing formation type                            | CGWB                                       | Geological dataset     |
| Aquifer thickness                   | Thickness of saturated aquifer                          | CGWB                                       | Hydrogeological data   |
| Aquifer transmissivity              | Groundwater transmission capacity                       | CGWB                                       | Hydrogeological study  |
| Groundwater recharge                | Estimated water added to aquifers                       | CGWB, recharge models                      | Model / assessment     |
| Groundwater extraction              | Estimated withdrawals                                   | CGWB                                       | Assessment             |
| Groundwater availability            | Available extractable resources                         | CGWB                                       | Assessment             |
| Groundwater quality                 | Dissolved chemistry and contaminants                    | CGWB, laboratory                           | Tests                  |
| Total dissolved solids              | Dissolved material concentration                        | Laboratory                                 | Testing                |
| Water pH                            | Acidity or alkalinity                                   | Laboratory                                 | Testing                |
| Water EC                            | Irrigation-water salinity                               | Laboratory                                 | Testing                |
| Sodium adsorption ratio             | Sodium hazard                                           | Laboratory, derived                        | Testing / calculation  |
| Chloride concentration              | Chloride content                                        | Laboratory                                 | Testing                |
| Fluoride concentration              | Fluoride content                                        | CGWB, laboratory                           | Testing                |
| Nitrate concentration               | Nitrate content                                         | CGWB, laboratory                           | Testing                |
| Surface soil moisture               | Near-surface moisture estimate                          | SMAP, ERA5-Land                            | Satellite / reanalysis |
| Root-zone soil moisture             | Moisture in deeper soil layers                          | SMAP L4, ERA5-Land                         | Model / reanalysis     |
| Actual evapotranspiration           | Actual water loss through evaporation and transpiration | MODIS ET, suitable satellite ET products   | Remote/model           |
| Irrigation coverage                 | Area receiving irrigation                               | Agricultural statistics, satellite mapping | GIS / statistics       |
| Irrigation infrastructure proximity | Distance to canals, reservoirs and water sources        | India-WRIS, mapped networks                | Spatial calculation    |
| Irrigation water demand             | Estimated irrigation requirement                        | ET0, crop parameters, soil data            | Model                  |

**Important farmer-collected variables:** borewell depth, yield/reliability, failure history, water pumping hours, irrigation frequency, irrigation method and irrigation costs.

These belong in the database even though they cannot reliably be obtained from satellite data.

Water quality must remain distinct from soil salinity. They are related but not interchangeable.

## **2.6 Historical land and vegetation**

| Characteristic               | Data to collect                                          | Primary source                                    | Method                   |
| ---------------------------- | -------------------------------------------------------- | ------------------------------------------------- | ------------------------ |
| Land cover                   | Forest, crop, grass, water, urban etc.                   | ESA WorldCover, Dynamic World                     | Satellite classification |
| Land use                     | Agricultural, residential, industrial etc.               | Bhuvan, land surveys                              | Maps / classification    |
| Crop type                    | Estimated crop grown in a season                         | Sentinel-2, Landsat, crop maps                    | Classification           |
| Cropping intensity           | Crop cycles per year                                     | Satellite classification, agricultural statistics | Derived                  |
| Cropping calendar            | Planting and harvesting timing                           | ICAR crop calendars, satellite time series        | Data / inference         |
| NDVI                         | Vegetation greenness                                     | Sentinel-2, Landsat, MODIS                        | Derived index            |
| EVI                          | Enhanced vegetation index                                | MODIS, Sentinel-2                                 | Derived index            |
| SAVI                         | Soil-adjusted vegetation index                           | Sentinel-2, Landsat                               | Derived index            |
| NDMI                         | Vegetation moisture-related index                        | Sentinel-2, Landsat                               | Derived index            |
| LAI                          | Leaf area index                                          | MODIS, Sentinel-2-derived products                | Product / estimate       |
| fAPAR                        | Fraction of absorbed photosynthetically active radiation | MODIS                                             | Satellite product        |
| Vegetation cover             | Proportion covered by vegetation                         | Sentinel-2, Landsat                               | Classification           |
| Phenology                    | Green-up, peak growth and senescence dates               | MODIS, Sentinel-2                                 | Time-series analysis     |
| Vegetation productivity      | Productivity over time                                   | MODIS                                             | Satellite product        |
| GPP                          | Gross primary productivity                               | MODIS                                             | Satellite/model product  |
| NPP                          | Net primary productivity                                 | MODIS                                             | Satellite/model product  |
| Above-ground biomass         | Estimated mass of above-ground vegetation                | Satellite products and models                     | Model                    |
| Tree cover                   | Percentage canopy cover                                  | Global Forest Watch, Landsat                      | Satellite                |
| Forest changes               | Forest gain/loss over time                               | Landsat, Global Forest Watch                      | Time series              |
| Vegetation anomalies         | Deviations from historical vegetation patterns           | NDVI/EVI historical series                        | Derived                  |
| Historical vegetation trends | Long-term vegetation trajectory                          | Landsat, MODIS, Sentinel-2                        | Derived                  |
| Burned area                  | Areas affected by fire                                   | MODIS, NASA FIRMS                                 | Satellite                |
| Crop stress indicators       | Abnormal growth, moisture and temperature conditions     | Sentinel-2, MODIS, ERA5-Land                      | Derived                  |

Sources:

- Sentinel-2 and Landsat through Google Earth Engine.
- MODIS through NASA LP DAAC or Earth Engine.
- ESA WorldCover.
- Dynamic World.
- JRC Global Surface Water.
- Global Forest Watch.
- NASA FIRMS.

**Historical crop identity is an inference unless there is a supporting agricultural record or labelled crop survey.** We should never automatically turn a vegetation index into a claimed crop species.

## **2.7 Environmental degradation and natural hazards**

| Characteristic              | Data to collect                          | Primary source                                  | Method                     |
| --------------------------- | ---------------------------------------- | ----------------------------------------------- | -------------------------- |
| Soil erosion susceptibility | Risk of water/wind erosion               | DEM, soil maps, RUSLE inputs                    | Model                      |
| Soil erosion rate           | Estimated soil loss per area per year    | RUSLE, field studies                            | Model                      |
| Land degradation            | Changes in land condition/productivity   | ISRO, Bhuvan, UNCCD                             | GIS / satellite            |
| Desertification risk        | Risk of arid land degradation            | ISRO, UNCCD                                     | Maps / model               |
| Waterlogging extent         | Extent of prolonged saturation           | Sentinel-1, field surveys                       | Satellite / survey         |
| Landslide susceptibility    | Probability of slope failure             | GSI, DEM, hazard maps                           | GIS / model                |
| Cyclone exposure            | Historical cyclone events affecting area | IMD, disaster records                           | Historical records         |
| Hailstorm occurrence        | Historical hail events                   | IMD, station records                            | Event records              |
| Wildfire risk               | Fire occurrence and susceptibility       | NASA FIRMS, MODIS                               | Satellite                  |
| Lightning frequency         | Historical lightning activity            | Lightning networks, available regional datasets | Sensor / event data        |
| Drought severity            | Historical drought intensity             | IMD, SPI, SPEI, vegetation anomalies            | Derived / official records |

## **2.8 Atmospheric and environmental quality**

| Characteristic        | Data to collect                  | Primary source                   | Method              |
| --------------------- | -------------------------------- | -------------------------------- | ------------------- |
| PM2.5                 | Fine particulate concentration   | CPCB, OpenAQ                     | Station / API       |
| PM10                  | Coarse particulate concentration | CPCB, OpenAQ                     | Station / API       |
| Aerosol optical depth | Atmospheric aerosol loading      | MODIS                            | Satellite           |
| Nitrogen dioxide      | Atmospheric NO₂                  | Sentinel-5P, CPCB                | Satellite / station |
| Sulphur dioxide       | Atmospheric SO₂                  | Sentinel-5P, CPCB                | Satellite / station |
| Carbon monoxide       | Atmospheric CO                   | Sentinel-5P                      | Satellite           |
| Ozone                 | Atmospheric ozone concentration  | Sentinel-5P, monitoring stations | Satellite / station |
| Air quality index     | Composite air quality assessment | CPCB                             | Portal / API        |

## **2.9 Crop-specific environmental requirements**

This dataset describes what each crop needs to grow successfully.

Unlike the environmental database, which describes what conditions exist on the land, this database describes the conditions each crop prefers and tolerates.

All requirements should be recorded by growth stage and, where possible, by cultivar.

| Characteristic                   | Data to collect                                                                    | Primary source                    | Acquisition method          |
| -------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------- | --------------------------- |
| Minimum temperature              | Minimum temperature tolerated                                                      | EcoCrop, ICAR, DSSAT              | Database / model parameters |
| Optimal temperature              | Ideal temperature for growth                                                       | EcoCrop, ICAR, APSIM              | Database / trials           |
| Maximum temperature              | Maximum tolerated temperature                                                      | EcoCrop, ICAR, DSSAT              | Database / trials           |
| Stage-specific temperature       | Temperature requirements at germination, vegetative growth, flowering and maturity | DSSAT, APSIM, ICAR                | Crop parameters             |
| Rainfall requirement             | Minimum, optimum and maximum rainfall                                              | EcoCrop, GAEZ, ICAR               | Crop database               |
| Soil pH tolerance                | Minimum, optimum and maximum pH                                                    | EcoCrop, ICAR                     | Crop database               |
| Soil texture preference          | Preferred sand, silt and clay fractions or texture class                           | EcoCrop, ICAR, crop trials        | Crop database               |
| Effective soil depth requirement | Minimum rooting depth                                                              | ICAR, DSSAT, APSIM                | Crop parameters             |
| Drainage preference              | Well-drained, moderately drained or poorly drained                                 | EcoCrop, ICAR                     | Crop database               |
| Nutrient requirements            | N, P, K, S and micronutrients                                                      | ICAR, DSSAT, APSIM                | Research / crop model       |
| Nutrient requirements by stage   | Nutrient demand at each developmental stage                                        | DSSAT, APSIM, ICAR trials         | Model / research            |
| Salinity tolerance               | Maximum acceptable soil EC                                                         | EcoCrop, ICAR, FAO research       | Crop database               |
| Salinity yield response          | Yield reduction at different EC levels                                             | ICAR research, crop trials        | Experimental data           |
| Altitude tolerance               | Minimum, optimum and maximum elevation                                             | EcoCrop, ICAR, GAEZ               | Crop database               |
| Growing-period requirements      | Minimum, optimum and maximum lifecycle duration                                    | EcoCrop, ICAR, FAO crop calendars | Crop database               |
| Photoperiod sensitivity          | Critical day length and flowering response                                         | DSSAT, APSIM, ICAR research       | Parameters / research       |
| Light requirements               | Light intensity and daily light integral requirements where available              | ICAR, crop physiology studies     | Research                    |
| Waterlogging preference          | Tolerance to saturated soil                                                        | ICAR, GAEZ, crop trials           | Research / trials           |
| Water availability preference    | Crop-specific water demand                                                         | FAO, DSSAT, APSIM                 | Model / research            |

### **Main crop-requirement sources**

| Source        | What we want to extract                                                   | Access category                            |
| ------------- | ------------------------------------------------------------------------- | ------------------------------------------ |
| FAO EcoCrop   | Temperature, rainfall, pH, texture, altitude, growing-period requirements | Database / portal; investigate bulk access |
| FAO GAEZ      | Agroecological suitability, potential yield and water-regime suitability  | GIS datasets / downloads                   |
| DSSAT         | Crop-specific parameters and environmental responses                      | Model software and parameter files         |
| APSIM         | Crop development, soil interaction and environmental response parameters  | Model software and parameter files         |
| ICAR          | Crop production manuals, agronomic requirements and Indian trials         | Research publications / institutional data |
| ICRISAT       | Dryland crop responses and field trials                                   | Research datasets / publications           |
| UAS Bengaluru | Karnataka crop recommendations and experiments                            | Research / institutional data              |
| UAS Dharwad   | Crop requirements and regional agricultural trials                        | Research / institutional data              |
| Local KVKs    | Region-specific agronomic recommendations                                 | Publications / direct data collection      |

Sources and requirements from the additional project document:&#x20;

Pasted text(5).txt



**Implementation note:** create one crop record for each species and separate cultivar records for varieties with materially different requirements. For each requirement, retain minimum, optimum and maximum values instead of reducing everything to one value.

## **2.10 Germination and early crop establishment**

This dataset determines whether a crop can successfully move from seed to established seedling.

| Characteristic                      | Data to collect                                            | Primary source                  | Acquisition method     |
| ----------------------------------- | ---------------------------------------------------------- | ------------------------------- | ---------------------- |
| Germination temperature minimum     | Minimum temperature allowing germination                   | ICAR, DSSAT, trials             | Research parameters    |
| Germination temperature optimum     | Ideal germination temperature                              | ICAR, trials                    | Research parameters    |
| Germination temperature maximum     | Upper germination temperature                              | ICAR, trials                    | Research parameters    |
| Germination rate                    | Percentage of seeds germinating under specified conditions | Seed-testing laboratories, ICAR | Laboratory             |
| Time to germination                 | Days/hours until germination                               | Seed laboratories, trials       | Experiment             |
| Seed emergence rate                 | Percentage of planted seeds emerging above soil            | ICAR, field trials              | Field experiment       |
| Emergence time                      | Time between sowing and emergence                          | Field trials, DSSAT             | Experiment / model     |
| Seedling establishment requirements | Moisture, temperature and soil conditions required         | ICAR, APSIM, DSSAT              | Research / simulation  |
| Seedling survival rate              | Percentage surviving the initial establishment period      | Crop trials, farmer records     | Field observations     |
| Early root growth                   | Root growth during establishment                           | DSSAT, APSIM, ICAR              | Model / root sampling  |
| Early root depth                    | Depth reached during early stages                          | ICAR, DSSAT, APSIM              | Experiment / model     |
| Early nutrient demand               | Nutrients consumed by seedlings                            | ICAR, DSSAT, APSIM              | Tissue testing / model |

**Primary sources:** ICAR, UAS Bengaluru, UAS Dharwad, agricultural universities, seed testing laboratories, DSSAT and APSIM.

These are not all available from public APIs. We will need to import experimental and laboratory results where applicable.

Pasted text(5).txt

## **2.11 Crop development and growth**

This dataset describes how a crop progresses throughout its lifecycle.

I recommend representing development as a time series, not merely a static record.

| Characteristic                     | Data to collect                                          | Primary source                    | Acquisition method      |
| ---------------------------------- | -------------------------------------------------------- | --------------------------------- | ----------------------- |
| Root growth rate                   | Root development per unit time                           | DSSAT, APSIM, trials              | Simulation / experiment |
| Root depth by growth stage         | Root depth during each stage                             | DSSAT, APSIM, ICAR                | Model / trials          |
| Leaf development rate              | Rate of leaf appearance                                  | DSSAT, APSIM                      | Model parameters        |
| Leaf area index                    | Leaf area relative to ground area                        | MODIS, Sentinel-2, ICAR           | Satellite / trials      |
| LAI development curve              | LAI at different growth stages                           | DSSAT, APSIM, MODIS               | Model / satellite       |
| Vegetative growth rate             | Increase in stems and leaves                             | DSSAT, APSIM, crop trials         | Model / field           |
| Biomass accumulation               | Dry matter production over time                          | DSSAT, APSIM, ICAR                | Model / weighing        |
| Flowering initiation               | Timing and triggering conditions for flowering           | DSSAT, APSIM, ICAR                | Model / field           |
| Flowering duration                 | Number of flowering days                                 | ICAR, APSIM, crop trials          | Research / observation  |
| Pollination type                   | Self-pollination, cross-pollination or other             | ICAR, crop manuals                | Crop database           |
| Pollinator dependence              | Degree of dependence on external pollinators             | ICAR, research papers             | Research                |
| Pollination window                 | Period during which pollination occurs                   | ICAR, crop trials                 | Field observations      |
| Fruit/pod/grain formation duration | Length of reproductive development                       | DSSAT, APSIM, ICAR                | Model / research        |
| Grain filling duration             | Time between grain formation and physiological maturity  | DSSAT, APSIM, ICAR                | Model / research        |
| Crop maturity duration             | Time to physiological maturity and harvest maturity      | FAO calendars, DSSAT, APSIM, ICAR | Dataset / model         |
| Harvest index                      | Harvested biomass relative to total above-ground biomass | DSSAT, APSIM, ICAR                | Model / trials          |
| Water-use efficiency               | Biomass or yield produced per unit of water consumed     | DSSAT, APSIM, ICAR                | Model / experiments     |
| Nutrient-use efficiency            | Production relative to nutrient uptake or application    | DSSAT, APSIM, ICAR                | Model / experiments     |

**Important associated variables:**

- Crop developmental stage.
- Days after sowing.
- Thermal time accumulated.
- Expected growth-stage start and end.
- Actual growth-stage observations.
- Crop-specific response to temperature and water stress.

For satellite-derived LAI, vegetation products and crop phenology, use Sentinel-2 and MODIS. For simulated growth curves, use DSSAT and APSIM.

Pasted text(5).txt

## **2.12 Crop performance and historical success**

This is a separate dataset from crop requirements.

It describes what actually happened when crops were grown under particular conditions.

| Characteristic                | Data to collect                                          | Primary source                                        | Acquisition method      |
| ----------------------------- | -------------------------------------------------------- | ----------------------------------------------------- | ----------------------- |
| Historical crop yield         | Actual yield per crop and season                         | FAOSTAT, ICAR, ICRISAT, state statistics              | Dataset / field records |
| Yield per hectare             | Standardized crop productivity                           | FAOSTAT, agricultural statistics                      | Dataset                 |
| Yield variability             | Variation between years and locations                    | FAOSTAT, ICAR, crop trials                            | Statistical analysis    |
| Crop failure frequency        | Frequency of failed crops                                | Field trials, farmer records, agricultural statistics | Field / survey          |
| Crop survival                 | Percentage of planted crop surviving                     | Field trials                                          | Observation             |
| Yield response to temperature | Change in yield under different temperatures             | ICAR, DSSAT, APSIM trials                             | Research / model        |
| Yield response to rainfall    | Change in yield under different rainfall conditions      | ICAR, ICRISAT, DSSAT                                  | Research / model        |
| Yield response to drought     | Yield losses under water stress                          | ICAR, ICRISAT, APSIM                                  | Research / model        |
| Yield response to heat        | Yield losses under heat stress                           | ICAR, DSSAT, crop trials                              | Research / model        |
| Yield response to salinity    | Yield changes at different EC levels                     | FAO, ICAR, field trials                               | Research / model        |
| Yield response to flooding    | Crop performance under waterlogging                      | ICAR, field trials                                    | Research / model        |
| Yield response to nutrients   | Effect of different nutrient conditions and applications | ICAR, DSSAT, APSIM                                    | Trials / model          |
| Cultivar performance          | Performance differences between varieties                | ICAR, UAS, seed trials                                | Research / records      |
| Biomass yield                 | Total plant biomass produced                             | ICAR, ICRISAT, crop trials                            | Field experiments       |
| Harvest quality               | Relevant crop-quality measurements                       | ICAR, agricultural universities                       | Laboratory / trials     |

Sources:

- FAOSTAT: historical crop production, area and yield statistics. Has a data API and downloadable data.
- ICAR and ICRISAT: research trials and performance results.
- State agriculture departments: crop production and yield statistics.
- Farmer records and plot-level trials: actual local performance.

A district-level historical yield record must not be presented as a measurement for an individual field. Store the geography of every performance record.

## **2.13 Crop stress tolerance and biological risks**

This domain should store both crop susceptibility and the organisms that cause agricultural damage.

| Characteristic                    | Data to collect                                                     | Primary source                              | Acquisition method   |
| --------------------------------- | ------------------------------------------------------------------- | ------------------------------------------- | -------------------- |
| Drought tolerance                 | Crop response to water shortage                                     | ICAR, DSSAT, APSIM, trials                  | Research / model     |
| Heat tolerance                    | Response to high temperatures                                       | ICAR, DSSAT, APSIM                          | Research / model     |
| Cold tolerance                    | Response to low temperatures                                        | ICAR, DSSAT, APSIM                          | Research / model     |
| Flooding tolerance                | Response to inundation and waterlogging                             | ICAR, GAEZ, crop trials                     | Research             |
| Stage-specific salinity tolerance | Salinity response at different stages                               | ICAR, FAO, trials                           | Research             |
| Pest susceptibility               | Pests affecting each crop and severity                              | NBAIR, ICAR, CABI                           | Databases / research |
| Disease susceptibility            | Diseases affecting each crop                                        | NBAIM, ICAR, CABI                           | Databases / research |
| Root disease susceptibility       | Root rot, wilt and soil-borne disease risk                          | NBAIM, ICAR, CABI                           | Research / diagnosis |
| Fungal diseases                   | Crop-specific fungal pathogens                                      | ICAR, CABI                                  | Databases / research |
| Bacterial diseases                | Crop-specific bacterial pathogens                                   | ICAR, CABI                                  | Databases / research |
| Viral diseases                    | Crop-specific viruses and vectors                                   | ICAR, CABI                                  | Databases / research |
| Weed competition tolerance        | Yield response to weed pressure                                     | ICAR, crop trials                           | Research             |
| Pollinator availability           | Presence and abundance of pollinators                               | ICAR, biodiversity surveys                  | Field surveys        |
| Environmental disease conditions  | Temperature, humidity and leaf wetness associated with disease risk | ICAR, weather station, leaf wetness sensors | Research / sensors   |

Sources:

- ICAR-NBAIR.
- ICAR-NBAIM.
- CABI.
- ICAR crop protection manuals.
- Crop-specific agricultural research.

**Storage distinction:** crop susceptibility is a crop property; actual pest and disease incidence is a field observation. Keep these separate. A crop can be susceptible to a disease without that disease ever being present in a particular field.

Pasted text(5).txt

## **2.14 Crop rotation and soil interactions**

[File:Crop Rotation.svg - Wikimedia Commons](https://images.openai.com/static-rsc-4/HVJue1TsxRqQjZfXcZ6OOOfT9wUC9twT8KdLvVlglNNUbR3mVrI_LICZjppQCjeC_w-ci1x4DYmMt3oR_ucsuavZo9l2DIuPovQn2-7cMs37VaF_6gBbsul7oxuWDn5jAw6zpGea1jFNuKi6MId1YA6CFJJ8jhxkpjonkwD4uN4?purpose=inline)

[commons.wikimedia.org](https://commons.wikimedia.org/wiki/File%3ACrop_Rotation.svg?utm_source=chatgpt.com)

This domain is one of the central components of the eventual project.

We need to store the changes caused by the previous crop, including both beneficial and harmful effects.

| Characteristic                | Data to collect                                         | Primary source                 | Acquisition method             |
| ----------------------------- | ------------------------------------------------------- | ------------------------------ | ------------------------------ |
| Nitrogen fixation capacity    | Amount of atmospheric nitrogen fixed                    | APSIM, DSSAT, ICAR, ICRISAT    | Model / research               |
| Nitrogen uptake               | Total nitrogen absorbed during growth                   | APSIM, DSSAT, ICAR             | Model / tissue tests           |
| Phosphorus uptake             | Total phosphorus absorbed                               | APSIM, DSSAT, ICAR             | Model / tissue tests           |
| Potassium uptake              | Total potassium absorbed                                | APSIM, DSSAT, ICAR             | Model / tissue tests           |
| Nutrient depletion            | Nutrients removed from the soil                         | APSIM, DSSAT, long-term trials | Model / before-after tests     |
| Nutrient replenishment        | Nutrients returned through fixation and residues        | APSIM, DSSAT, ICAR             | Model / experiments            |
| Crop residue production       | Mass of stems, leaves and other residual material       | APSIM, DSSAT, trials           | Model / weighing               |
| Residue composition           | Carbon, nitrogen and other relevant residue contents    | ICAR, laboratory               | Lab / research                 |
| Residue decomposition rate    | Speed of residue breakdown                              | APSIM, DSSAT, experiments      | Model / experiments            |
| Root residue contribution     | Root material left in soil                              | APSIM, DSSAT, trials           | Model / root sampling          |
| Organic matter contribution   | Change in soil organic matter                           | APSIM, long-term experiments   | Model / soil tests             |
| Soil structure improvement    | Changes to aggregation and compaction                   | APSIM, ICAR, field trials      | Model / physical tests         |
| Soil moisture carryover       | Remaining soil moisture after harvesting                | APSIM, DSSAT                   | Model / probes                 |
| Crop water consumption        | Water consumed over entire crop lifecycle               | DSSAT, APSIM, satellite ET     | Model / satellite              |
| Allelopathic effects          | Chemical interference with following crops              | ICAR, research studies         | Laboratory / field experiments |
| Shared pest and disease risks | Common hosts and pathogens in successive crops          | ICAR, CABI, NBAIR, NBAIM       | Biological databases           |
| Crop family compatibility     | Botanical family and related crop species               | FAO, ICAR, crop taxonomy       | Reference database             |
| Rotation interval             | Recommended time before repeating the same/related crop | ICAR, UAS, KVK                 | Agronomic recommendations      |
| Nutrient carryover            | Nutrient effects from the preceding crop                | APSIM, DSSAT, long-term trials | Simulation / experiments       |

For good rotation modelling, add a structured relationship between crop A and crop B, with fields for:

- Preceding crop.
- Following crop.
- Environmental conditions.
- Soil condition before the preceding crop.
- Soil condition after the preceding crop.
- Nutrient changes.
- Soil moisture changes.
- Residue quantity and decomposition.
- Pest and disease carryover.
- Observed yield effect on the following crop.
- Study region and evidence source.

**Primary source: APSIM.** Its simulation capabilities make it particularly relevant to modelling successive cropping seasons. DSSAT is another major source for crop growth, water and nitrogen processes.

ICRISAT and ICAR long-term field trials should be used to find empirical evidence and validate simulations.

Pasted text(5).txt

## **2.15 Cultivation and crop management**

This is the information required to understand how the crop was actually cultivated, rather than simply what the environmental conditions were.

| Characteristic                | Data to collect                              | Primary source                                | Acquisition method         |
| ----------------------------- | -------------------------------------------- | --------------------------------------------- | -------------------------- |
| Actual sowing date            | Date crop was planted                        | Farmer records                                | Questionnaire              |
| Recommended sowing window     | Recommended planting period                  | ICAR, UAS, KVK                                | Crop calendars             |
| Actual harvesting date        | Date crop was harvested                      | Farmer records                                | Questionnaire              |
| Recommended harvesting window | Expected harvest period                      | ICAR, UAS, KVK                                | Crop calendars             |
| Crop cultivar / variety       | Exact planted variety                        | ICAR, seed databases, farmer records          | Database / questionnaire   |
| Seed germination percentage   | Seed viability result                        | Seed-testing laboratories                     | Laboratory                 |
| Seed purity                   | Physical and varietal purity                 | Seed-testing laboratories                     | Laboratory                 |
| Seed viability                | Percentage of viable seeds                   | Seed-testing laboratories                     | Laboratory                 |
| Seed rate                     | Quantity of seed per area                    | ICAR, UAS, farmer records                     | Research / questionnaire   |
| Plant population              | Plants per square metre/hectare              | ICAR, field observations                      | Field counts               |
| Row spacing                   | Distance between rows                        | ICAR, UAS, farmer records                     | Measurements               |
| Planting depth                | Depth at which seed is planted               | ICAR, farmer records                          | Measurements               |
| Irrigation schedule           | Timing and frequency                         | Farmer records, APSIM/DSSAT management inputs | Questionnaire / simulation |
| Irrigation volume             | Actual volume applied                        | Farmer records, flow meter                    | Sensor / questionnaire     |
| Fertilizer application        | Product, quantity and timing                 | ICAR, UAS, farmer records                     | Questionnaire              |
| Tillage practices             | Method, frequency and depth                  | ICAR, farmer records                          | Questionnaire              |
| Weed management               | Manual, mechanical and chemical control      | ICAR, farmer records                          | Questionnaire              |
| Pest management               | Treatment and control practices              | ICAR, farmer records                          | Questionnaire              |
| Pesticide application         | Product, dosage and dates                    | Farmer records                                | Questionnaire              |
| Organic amendments            | Manure, compost and other organic inputs     | Farmer records, ICAR                          | Questionnaire              |
| Residue management            | Removal, burning, incorporation or retention | Farmer records                                | Questionnaire              |
| Harvesting method             | Manual or mechanized method                  | Farmer records                                | Questionnaire              |

Sources:

- ICAR crop production packages.
- UAS Bengaluru and UAS Dharwad.
- Local KVKs.
- Seed certification and testing agencies.
- Farmer questionnaires.
- DSSAT and APSIM management input records.

Pasted text(5).txt

## **2.16 Physical sensor inventory**

These are the field devices that would allow us to measure conditions that satellite or historical datasets cannot reliably resolve.

| Sensor / instrument                | Data collected                                            | Supporting data domains                 |
| ---------------------------------- | --------------------------------------------------------- | --------------------------------------- |
| Soil moisture probe                | Volumetric water content at different depths              | Soil, water, crop development, rotation |
| Soil temperature probe             | Soil temperature at different depths                      | Soil, germination, development          |
| Automatic weather station          | Temperature, humidity, wind, rainfall and solar radiation | Climate, crop stress                    |
| Rain gauge                         | Local rainfall                                            | Rainfall                                |
| Soil pH meter / laboratory         | Soil acidity                                              | Soil, suitability                       |
| Soil EC meter / laboratory         | Salinity                                                  | Soil, suitability                       |
| NPK testing equipment / laboratory | Soil nutrients                                            | Soil, rotation                          |
| Plant tissue testing               | Actual nutrient uptake                                    | Development, rotation                   |
| PAR sensor                         | Photosynthetically active radiation                       | Crop requirements and growth            |
| LAI meter                          | Leaf area index                                           | Crop development                        |
| Irrigation flow meter              | Water volume applied                                      | Water, management                       |
| Leaf wetness sensor                | Duration of leaf wetness                                  | Biological disease risk                 |
| Root sampling tools                | Root depth and biomass                                    | Development, rotation                   |
| Plant biomass sampling equipment   | Biomass accumulation                                      | Development, performance                |

The first seven instruments were identified in your uploaded data acquisition plan; root and biomass sampling are included to support the crop-growth and rotation variables.&#x20;

Pasted text(5).txt



**Sensor deployment strategy:** do not install every sensor in every field. Start with a small pilot network, combine it with satellite and public data, and use measured field observations to validate the estimates.

# **3. Complete source and API acquisition directory**

We now have a list of what data to collect. The next task is identifying exactly how each source enters our system.

I recommend classifying every source into one of five acquisition types.

| Type                       | Meaning                                                    | Example                       |
| -------------------------- | ---------------------------------------------------------- | ----------------------------- |
| REST API                   | Send a request and receive structured data                 | NASA POWER                    |
| Geospatial API             | Query spatial datasets or imagery                          | Google Earth Engine           |
| Downloadable dataset       | Download raster, vector or tabular files                   | WorldClim, GAEZ               |
| Scientific model           | Run simulations using input data and parameters            | APSIM, DSSAT                  |
| Manual / field acquisition | Collect laboratory measurements, records or questionnaires | Soil Health Card, farmer data |

This distinction matters. We should not design an API integration for a source that only supplies downloadable GIS files or a model executable.

## **3.1 Source registry**

This is the complete source registry I recommend starting with.

Access methods below are the intended integration paths, not live-verified November 2026 endpoint guarantees.

| Source                      | Data we will use                                 | Access method                                    | Authentication / access consideration    |
| --------------------------- | ------------------------------------------------ | ------------------------------------------------ | ---------------------------------------- |
| SoilGrids                   | Soil properties                                  | REST API, GeoTIFF                                | API access; verify service limits        |
| Soil Health Card            | Laboratory soil chemistry                        | Report import, authorized data access            | Public bulk API not assumed              |
| NBSS&LUP                    | Soil maps and classification                     | GIS data / institutional request                 | Dataset access                           |
| NASA POWER                  | Daily and monthly climate                        | REST API                                         | Generally public access                  |
| KSNDMC                      | Karnataka station rainfall and weather           | Portal / data request                            | Verify station-data availability         |
| IMD                         | Weather, rainfall and climate                    | Downloads / station data                         | Access conditions vary                   |
| CHIRPS                      | Historical rainfall                              | Raster downloads / Earth Engine                  | Dataset access                           |
| GPM IMERG                   | Satellite precipitation                          | NASA Earthdata / Earth Engine                    | Product and account conditions           |
| ERA5-Land                   | Weather and soil moisture                        | Copernicus Climate Data Store API / Earth Engine | CDS account and API configuration        |
| TerraClimate                | Monthly climate and water balance                | Raster downloads / Earth Engine                  | Dataset access                           |
| WorldClim                   | Climate averages and projections                 | Downloadable rasters                             | Dataset access                           |
| CMIP6                       | Future climate simulations                       | ESGF / climate datasets                          | Large downloads                          |
| Copernicus DEM              | Elevation                                        | Raster downloads / Copernicus services           | Product-specific access                  |
| SRTM                        | Elevation                                        | NASA Earthdata / Earth Engine                    | Dataset access                           |
| ALOS                        | Elevation                                        | JAXA data services / available raster datasets   | Product-specific access                  |
| HydroSHEDS                  | Drainage and watersheds                          | GIS downloads / Earth Engine where available     | Dataset access                           |
| GSI                         | Geology and lithology                            | GIS maps / data requests                         | Dataset access                           |
| Bhuvan                      | Indian land and thematic maps                    | Geoportal / available services                   | Service-specific access                  |
| CGWB                        | Groundwater and aquifer information              | Portal / datasets / official request             | Do not assume a complete public API      |
| India-WRIS                  | Water resources and infrastructure               | Portal / GIS products                            | Verify downloadable services             |
| NASA SMAP                   | Surface and root-zone soil moisture              | NASA Earthdata / Earth Engine                    | Product-specific access                  |
| JRC Global Surface Water    | Historical surface water                         | Earth Engine / downloadable raster               | Dataset access                           |
| Sentinel-1                  | Radar, flooding and land observations            | Copernicus Data Space / Earth Engine             | Account or API access depending on route |
| Sentinel-2                  | Vegetation, crop and land observations           | Copernicus Data Space / Earth Engine             | Account or API access depending on route |
| Landsat                     | Long-term vegetation and land changes            | USGS/NASA / Earth Engine                         | Product-specific access                  |
| MODIS                       | LAI, fAPAR, GPP, NPP, vegetation and ET products | NASA LP DAAC / Earth Engine                      | Product-specific access                  |
| ESA WorldCover              | Land-cover classification                        | Downloadable rasters                             | Dataset access                           |
| Dynamic World               | Land-cover classification                        | Google Earth Engine                              | Earth Engine access                      |
| Global Forest Watch         | Tree cover and forest loss                       | Data downloads / API where available             | Product-specific terms                   |
| NASA FIRMS                  | Fires and thermal anomalies                      | API / downloads                                  | API key for certain interfaces           |
| Sentinel-5P                 | Atmospheric pollutants                           | Copernicus / Earth Engine                        | Product-specific access                  |
| CPCB                        | Indian air and water quality                     | Portal / available APIs                          | Verify API and licensing                 |
| OpenAQ                      | Air quality station observations                 | REST API                                         | API terms and coverage                   |
| FAO EcoCrop                 | Crop requirements                                | Database / portal                                | Investigate bulk export                  |
| FAO GAEZ                    | Crop suitability and yield potential             | GIS downloads                                    | Dataset access                           |
| DSSAT                       | Crop development and response                    | Model software / parameter files                 | Installation and model licensing         |
| APSIM                       | Crop growth and rotation processes               | Model software / parameter files                 | Installation and licensing               |
| FAOSTAT                     | Historical production and yields                 | REST API / downloads                             | Check dataset coverage                   |
| ICAR                        | Indian agronomy and crop trials                  | Research publications / data request             | Institutional sources                    |
| ICRISAT                     | Dryland crop research and trials                 | Research datasets / publications                 | Dataset-specific terms                   |
| UAS Bengaluru               | Regional crops and trials                        | Publications / institutional requests            | Institutional access                     |
| UAS Dharwad                 | Regional crops and trials                        | Publications / institutional requests            | Institutional access                     |
| KVKs                        | Regional cultivation recommendations             | Publications / farmer interaction                | Manual / institutional                   |
| NBAIR                       | Pest and insect information                      | Portal / publications / institutional data       | Verify data access                       |
| NBAIM                       | Agricultural microorganisms and diseases         | Portal / research / institutional data           | Verify data access                       |
| CABI                        | Pests, diseases and crop biology                 | Database / publications                          | Some content may require licensing       |
| Seed testing agencies       | Germination, seed purity and viability           | Laboratory reports                               | Manual / laboratory                      |
| Soil and water laboratories | Soil and irrigation water chemistry              | Test reports                                     | Manual / laboratory                      |
| Farmer questionnaires       | Management and historical field information      | Form / structured imports                        | Direct collection                        |
| Field sensors               | Soil, atmospheric and crop observations          | Sensor exports / MQTT / CSV                      | Hardware-specific                        |

## **3.2 API integrations to develop first**

These are the interfaces I would put at the top of our implementation list.

**1. SoilGrids**

First soil integration

REST API

`https://rest.isric.org/soilgrids/v2.0/properties/query`

Retrieves soil property estimates for a coordinate. We will need to extract the relevant values and depth intervals for each field, subject to the API's supported query structure and limits.

**2. NASA POWER**

First climate integration

REST API

`https://power.larc.nasa.gov/api/temporal/daily/point`

Retrieve daily temperature, rainfall, humidity and radiation data. Store the original daily responses rather than only the annual summaries.

**3. Google Earth Engine**

First satellite integration

Python / JavaScript API

`https://earthengine.google.com/`

Use this to process Sentinel-2, Landsat, MODIS, SMAP and other available collections. This will be our main historical satellite processing platform.

**4. FAOSTAT**

Crop statistics

REST API / downloads

`https://www.fao.org/faostat/`

Retrieve available crop production, area and yield statistics.

**5. Copernicus Climate Data Store**

Climate expansion

CDS API

`https://cds.climate.copernicus.eu/`

Retrieve ERA5-Land historical climate and land variables.

## **3.3 Sources that require a different strategy**

Some of our most valuable sources should not be forced into an API architecture.

| Source                    | Recommended approach                                                                |
| ------------------------- | ----------------------------------------------------------------------------------- |
| Soil Health Card          | Import individual or bulk authorized soil reports                                   |
| KSNDMC                    | Obtain station records through available downloads or a formal request              |
| CGWB                      | Download observation-well and aquifer datasets; maintain station-level metadata     |
| EcoCrop                   | Investigate structured export of crop profiles                                      |
| GAEZ                      | Download relevant crop suitability and yield layers                                 |
| DSSAT                     | Extract crop parameters from supported model files and run simulations              |
| APSIM                     | Use its model inputs and simulation outputs                                         |
| ICAR                      | Build a structured research-data import process                                     |
| ICAR/ICRISAT trials       | Import actual observations with their location, variety and experimental conditions |
| CABI                      | Use permitted database access or licensed material                                  |
| Farmer records            | Build a standardized questionnaire                                                  |
| Soil testing laboratories | Import CSV/Excel reports and structured laboratory records                          |

**A key architectural decision:** the acquisition system must be modular. A missing API should not prevent us from using a source. For instance, a CSV from KSNDMC should be usable in exactly the same downstream rainfall-processing pipeline as data retrieved from a REST API.

# **4. How the KML file controls data acquisition**

This is the most important part of the entire implementation.

We want to be able to provide a KML file, select one or more plots, and have the system retrieve data associated with those geographical boundaries.

A KML file is a geographical selection mechanism. It does not itself contain the environmental information we want.

## **4.1 Expected KML input**

A KML can contain several polygons, each representing a different field.

[- YouTube](https://images.openai.com/static-rsc-4/Abu2D7mLUxBx60BkCRtou-AwLxvPYIH5ACiM8zfMjX6E0Mm2CQYeXhowRdtSxFNixxvntxdIwkkLtkwvAtMoAOxz3mKOja7BuTnA0LoVV_2WCbLkderECzat2E-826u3XDPrvYLLulo6V0CEEWJ0vknzw59vUXhdTKLym6PPiaM?purpose=inline)

[youtube.com](https://www.youtube.com/watch?v=Ol3s13wGSzw\&utm_source=chatgpt.com)

The program should support:

- One polygon.
- Multiple polygons.
- MultiPolygon features.
- Polygon holes.
- Named placemarks.
- KML folders.
- KMZ files.
- Optional metadata attached to placemarks.

Every polygon should become a separate `field_id`.

Example:

```
farm_area.kml
    |
    |-- North Field
    |-- South Field
    |-- Irrigated Field
    |-- Dryland Field
```

We will create:

```
FIELD_0001
FIELD_0002
FIELD_0003
FIELD_0004
```

Each field gets its own set of environmental observations.

We can additionally calculate the union of all polygons for a whole-farm or regional analysis, but we must preserve individual field records.

## **4.2 KML processing workflow**

1. **Read the KML**

   Use `geopandas`, GDAL/Fiona or an appropriate KML reader to extract placemarks and polygon geometries.
2. **Identify individual polygons**

   Extract names, IDs, folders and associated metadata. Create stable field identifiers.
3. **Validate geometry**

   Check invalid polygons, empty geometries, self-intersections, holes and multiple polygon components. Repair only when valid repair is possible and record any correction.
4. **Standardize coordinate systems**

   KML coordinates are normally WGS84 (EPSG:4326). Preserve them, and create suitable projected versions for area and distance calculations.
5. **Calculate plot measurements**

   Calculate area, perimeter, bounding box and centroid/representative point.
6. **Create an area of interest (AOI)**

   Pass the actual polygon geometry to each relevant data source or processing pipeline.
7. **Determine data coverage**

   Identify which grids, rasters, stations and vector datasets intersect the polygon.
8. **Acquire and process data**

   Query the source, clip or extract its information, and calculate plot-level statistics.
9. **Store everything**

   Save raw source files, normalized observations, derived variables and provenance metadata.

## **4.3 Coordinate system handling**

We need to pay attention to coordinate systems because different data sources use different projections.

Recommended internal conventions:

| Purpose                     | Coordinate system                                  |
| --------------------------- | -------------------------------------------------- |
| Original KML                | EPSG:4326                                          |
| Earth Engine geometry input | WGS84 longitude/latitude                           |
| Local distance and area     | Appropriate local projected CRS                    |
| Broad area calculations     | Equal-area CRS such as EPSG:6933                   |
| Raster processing           | Native source CRS, unless reprojection is required |

For an Indian pilot, suitable UTM zones depend on the field's longitude. Do not assign one UTM zone blindly to every location in India.

Area must not be calculated directly using latitude/longitude coordinates.

## **4.4 How each source uses the KML geometry**

Different datasets require different spatial extraction methods.

| Dataset type               | What the system should do with the polygon                                                               |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| SoilGrids                  | Query supported locations or extract intersecting raster pixels                                          |
| Soil Health Card           | Associate imported soil samples with their field/sample coordinates                                      |
| NASA POWER                 | Query a representative point and record the coarse grid resolution                                       |
| KSNDMC                     | Find nearby stations and calculate distances                                                             |
| IMD rainfall grids         | Extract intersecting precipitation pixels                                                                |
| CHIRPS                     | Clip/intersect rainfall raster and calculate statistics                                                  |
| GPM IMERG                  | Extract intersecting rainfall grid cells                                                                 |
| ERA5-Land                  | Clip or extract gridded time series                                                                      |
| DEM                        | Extract elevation pixels and derive terrain variables                                                    |
| CGWB                       | Find relevant monitoring wells, groundwater assessment regions and aquifers                              |
| India-WRIS                 | Intersect plot with watersheds, rivers, canals and water infrastructure                                  |
| SMAP                       | Extract intersecting soil moisture cells                                                                 |
| Sentinel-2                 | Filter imagery by plot boundary, date and cloud cover                                                    |
| Landsat                    | Filter scenes by plot, date and cloud quality                                                            |
| MODIS                      | Extract available pixels or product time series                                                          |
| JRC Water                  | Determine water occurrence within and around the polygon                                                 |
| ESA WorldCover             | Calculate land-cover distribution within the field                                                       |
| Dynamic World              | Calculate land-cover class probabilities and distributions                                               |
| FIRMS                      | Find historical fire detections within or near the region                                                |
| Sentinel-5P                | Extract relevant atmospheric grid observations, subject to product resolution                            |
| Crop trials                | Spatially select experiments within a chosen surrounding region                                          |
| Crop requirement databases | Join crop profiles with the environmental profile; requirements are not usually geographically extracted |
| APSIM / DSSAT              | Build simulations using the extracted environment, crop parameters and management inputs                 |
| Farmer questionnaire       | Associate answers with the corresponding `field_id`                                                      |

### **Special case: nearby weather stations and groundwater wells**

For station-based data, the polygon intersection alone is not enough.

We should also calculate:

- Nearest station.
- Distance from field centroid to station.
- Number of stations within configurable radii.
- Elevation difference, where available.
- Available historical observation period.
- Whether the station is representative of the plot.

For example, the nearest rain gauge may be farther away than another station with better elevation and climatic representativeness.

We should preserve the station selection information rather than simply claiming that its reading was measured on the field.

## **4.5 Raster extraction: the most important geospatial operation**

Most of the soil, terrain, climate and satellite information comes as raster pixels.

For a field polygon, we must calculate the statistics of the pixels intersecting the polygon.

[XTools Pro Help - Extract Raster Zonal Statistics](https://images.openai.com/static-rsc-4/YQUBVN5FMzQQjFpbJMf-d-3MVem8XBcNxaAGOawViqFUOJUMs3sYX3PQgMDI3uPM52qJ3_XPW_n37V97pOygIdE299-Hw9sWZfCygll8kj3hwTDxL1iGsgVj7JjtJaTIgiN0mlpDr2Yu1AyhJsoMKidXX7pgOjVKNsPXcMSrRyw?purpose=inline)

[help.xtools.pro](https://help.xtools.pro/pro/24.0/en/XTools_Pro_Components/Raster_Tools/Extract_Raster_Zonal_Statistics.htm?utm_source=chatgpt.com)

For each variable, calculate the supported statistics:

| Statistic             | Purpose                                    |
| --------------------- | ------------------------------------------ |
| Mean                  | Average value across the plot              |
| Median                | Typical value, less affected by outliers   |
| Minimum               | Lowest intersecting value                  |
| Maximum               | Highest intersecting value                 |
| Standard deviation    | Spatial variation                          |
| 10th percentile       | Lower-end distribution                     |
| 90th percentile       | Upper-end distribution                     |
| Valid pixel count     | Number of usable pixels                    |
| Valid area percentage | Amount of plot represented by valid pixels |

For rainfall and climate, also calculate temporal statistics:

- Daily values.
- Monthly totals or averages.
- Seasonal totals or averages.
- Annual values.
- Long-term trends.
- Anomalies.

For soil, keep depth-specific values. For vegetation, keep time-specific observations.

### **Resolution is critical**

Suppose a field occupies 2 hectares while the underlying product has 250 m pixels.

The source pixel covers a substantially larger geographical area than the field. We cannot truthfully claim that the field has a precisely measured soil characteristic at 250 m resolution.

The database should store:

```
field_id: FIELD_0001
source: SoilGrids
variable: soil_pH
depth: 0-5 cm
source_resolution_m: 250
spatial_support: gridded estimate
extraction_method: intersecting pixel
measurement_type: modelled
```

Likewise, a 9 km soil-moisture product cannot resolve individual neighboring agricultural plots.

**Never resample a coarse dataset to 10 m and imply that the new 10 m values contain 10 m information.**

We should preserve the original resolution and calculate the uncertainty/coverage appropriately.

## **4.6 Spatial buffers and regional context**

Some information is more useful when collected beyond the exact field boundary.

We should support optional buffers around each plot.

| Buffer              | Potential use                                                  |
| ------------------- | -------------------------------------------------------------- |
| Field boundary only | Soil, vegetation and land-cover extraction                     |
| 100 m               | Immediate surroundings, drainage and localized land context    |
| 500 m               | Nearby water bodies and land-cover context                     |
| 1 km                | Local environmental and infrastructure context                 |
| 5 km                | Wider landscape and hydrological context                       |
| 10 km or more       | Weather station and regional groundwater context, where useful |

These distances are configurable examples, not universal scientific thresholds. Station matching and aquifer matching should use their own rules.

Store buffer observations separately from field observations so that surrounding land never gets mistaken for the farm itself.

# **5. Local storage architecture**

Now we need to design where everything actually lives.

I recommend using **PostgreSQL with PostGIS as the central local database**, combined with filesystem-based storage for large geospatial files.

Do not store every raw satellite image inside PostgreSQL. Store the file on disk and keep its location, metadata and extraction information in the database.

## **5.1 Technology selection**

| Component                  | Recommended technology            | Role                                             |
| -------------------------- | --------------------------------- | ------------------------------------------------ |
| Main database              | PostgreSQL                        | Structured records                               |
| Spatial database           | PostGIS                           | Field boundaries and geographical queries        |
| Raster files               | GeoTIFF / Cloud Optimized GeoTIFF | Spatial raster storage                           |
| Climate arrays             | NetCDF / Zarr                     | Large multidimensional time series               |
| Satellite source files     | GeoTIFF / HDF5 / NetCDF           | Original product preservation                    |
| Tabular storage            | Parquet                           | Efficient local analytical datasets              |
| Interchange                | CSV / JSON                        | Easy imports and exports                         |
| Vector storage             | GeoPackage / GeoParquet           | GIS datasets                                     |
| Notebook environment       | JupyterLab                        | Exploration and documentation                    |
| Processing                 | Python                            | API, raster, vector and analytical processing    |
| Optional analytical engine | DuckDB                            | Fast analytical queries over local Parquet files |

My recommendation is to start with PostgreSQL/PostGIS, not to build multiple database systems immediately. DuckDB can be added if local analytical queries over large Parquet datasets become a bottleneck.

## **5.2 Project directory structure**

I recommend structuring the local project like this:

```
agriculture-data-project/
│
├── README.md
├── pyproject.toml
├── requirements.txt
├── .env
├── .env.example
├── docker-compose.yml
│
├── config/
│   ├── project.yaml
│   ├── sources.yaml
│   ├── variables.yaml
│   ├── crop_catalog.yaml
│   └── processing.yaml
│
├── data/
│   │
│   ├── raw/
│   │   ├── soilgrids/
│   │   ├── soil_health_card/
│   │   ├── nasa_power/
│   │   ├── ksndmc/
│   │   ├── imd/
│   │   ├── chirps/
│   │   ├── era5_land/
│   │   ├── cgwb/
│   │   ├── india_wris/
│   │   ├── sentinel_1/
│   │   ├── sentinel_2/
│   │   ├── landsat/
│   │   ├── modis/
│   │   ├── dem/
│   │   ├── crop_databases/
│   │   └── field_observations/
│   │
│   ├── staging/
│   │
│   ├── normalized/
│   │   ├── soil/
│   │   ├── climate/
│   │   ├── water/
│   │   ├── terrain/
│   │   ├── vegetation/
│   │   └── crop_data/
│   │
│   ├── processed/
│   │   ├── fields/
│   │   ├── soil/
│   │   ├── climate/
│   │   ├── water/
│   │   ├── terrain/
│   │   ├── vegetation/
│   │   ├── crop_profiles/
│   │   ├── performance/
│   │   ├── biological_risks/
│   │   ├── rotation/
│   │   └── management/
│   │
│   ├── derived/
│   │   ├── climate_indicators/
│   │   ├── soil_indicators/
│   │   ├── vegetation_indices/
│   │   ├── crop_suitability_inputs/
│   │   └── rotation_indicators/
│   │
│   ├── exports/
│   │
│   └── cache/
│
├── notebooks/
│   ├── 00_project_overview.ipynb
│   ├── 01_environment_setup.ipynb
│   ├── 02_kml_ingestion.ipynb
│   ├── 03_geospatial_processing.ipynb
│   ├── 04_source_registry.ipynb
│   ├── 05_soil_data.ipynb
│   ├── 06_climate_data.ipynb
│   ├── 07_climate_indicators.ipynb
│   ├── 08_terrain_geology.ipynb
│   ├── 09_water_data.ipynb
│   ├── 10_satellite_data.ipynb
│   ├── 11_vegetation_indices.ipynb
│   ├── 12_crop_requirements.ipynb
│   ├── 13_germination_development.ipynb
│   ├── 14_crop_performance.ipynb
│   ├── 15_biological_risks.ipynb
│   ├── 16_crop_rotation.ipynb
│   ├── 17_cultivation_management.ipynb
│   ├── 18_sensor_data.ipynb
│   ├── 19_database_integration.ipynb
│   └── 20_end_to_end_test.ipynb
│
├── src/
│   └── agri_data/
│       ├── __init__.py
│       ├── config.py
│       ├── geo/
│       ├── sources/
│       ├── processing/
│       ├── crop/
│       ├── rotation/
│       ├── storage/
│       └── reporting/
│
├── tests/
│   ├── test_kml.py
│   ├── test_geometry.py
│   ├── test_soilgrids.py
│   ├── test_climate.py
│   ├── test_raster_extraction.py
│   ├── test_units.py
│   └── test_database.py
│
├── docs/
│   ├── data_dictionary.md
│   ├── source_catalog.md
│   ├── database_schema.md
│   ├── kml_workflow.md
│   └── methodology.md
│
└── logs/
```

The actual storage directory should be configurable. For large satellite datasets, I would place `data` on a separate disk or volume rather than necessarily inside the project source directory.

## **5.3 How we organize raw data**

Each downloaded dataset should be stored using a consistent naming convention.

Example:

```
data/raw/
    nasa_power/
        daily/
            2020/
                FIELD_0001.json
                FIELD_0002.json
            2021/
                FIELD_0001.json
```

For satellite imagery:

```
data/raw/
    sentinel_2/
        2024/
            FIELD_0001/
                S2_scene_001.tif
                S2_scene_002.tif
                metadata.json
```

For SoilGrids:

```
data/raw/
    soilgrids/
        FIELD_0001/
            soilgrids_response.json
            metadata.json
```

We should store raw data by source and dataset, not simply by field. Some raster products will be shared between many adjacent fields, and downloading the same source pixel repeatedly is wasteful.

## **5.4 How processed data is stored**

Use Parquet for most tabular data.

Example:

```
data/processed/climate/
    field_id=FIELD_0001/
        year=2020/
            daily_weather.parquet
        year=2021/
            daily_weather.parquet
```

This enables fast filtering by field and year without loading a large CSV.

For satellite products:

```
data/processed/vegetation/
    FIELD_0001/
        ndvi/
            2024_01.tif
            2024_02.tif
            2024_03.tif
        ndmi/
            2024_01.tif
            2024_02.tif
```

For final agricultural profiles:

```
data/exports/
    FIELD_0001/
        environmental_profile.json
        crop_profile.json
        historical_vegetation.parquet
```

These are exports, not the primary source of truth. The database and original files remain authoritative.

# **6. Database design**

The directory structure tells us where the files live. We also need a proper database that connects all of them.

I recommend a relational database with a flexible observation system.

The important principle is that **one field can have thousands of observations, and one environmental variable can have multiple values from different sources.**

For example, the soil pH of one field could have:

- SoilGrids estimate at 0–5 cm.
- SoilGrids estimate at 5–15 cm.
- Soil Health Card laboratory measurement.
- A later field measurement.

All four must be preserved.

## **6.1 Database tables**

I would start with these tables.

| Table                   | Stored information                                         |
| ----------------------- | ---------------------------------------------------------- |
| `projects`              | Project identity and configuration                         |
| `fields`                | Individual agricultural plot IDs and geometries            |
| `field_boundaries`      | Original and revised KML geometries                        |
| `data_sources`          | Source registry and acquisition details                    |
| `datasets`              | Individual datasets and product versions                   |
| `variables`             | Master data dictionary                                     |
| `source_assets`         | File locations, metadata, checksums and original downloads |
| `extraction_jobs`       | Acquisition and processing job history                     |
| `observations`          | Environmental and sensor measurements                      |
| `crop_species`          | Crop species and taxonomy                                  |
| `crop_varieties`        | Cultivars and varieties                                    |
| `crop_growth_stages`    | Standardized growth-stage definitions                      |
| `crop_parameters`       | Environmental requirements and growth parameters           |
| `crop_trials`           | Experimental trial information and locations               |
| `crop_performance`      | Actual crop yields and observed outcomes                   |
| `biological_agents`     | Pests, diseases, pathogens and weeds                       |
| `crop_biological_risks` | Crop susceptibility to biological threats                  |
| `rotation_effects`      | Effects of one crop on another                             |
| `management_events`     | Sowing, fertilizer, irrigation, tillage and other events   |
| `farmer_surveys`        | Questionnaire submissions                                  |
| `sensor_deployments`    | Sensor location, type, depth and installation details      |
| `sensor_readings`       | Time-series sensor observations                            |

## **6.2 The master observations table**

Rather than creating a separate table for every soil or climate measurement, use a normalized observation structure.

Example:

| observation_id | field_id   | variable        | value | unit | date       | source     |
| -------------- | ---------- | --------------- | ----- | ---- | ---------- | ---------- |
| 1              | FIELD_0001 | soil_ph         | 6.4   | pH   | 2026-01-01 | SoilGrids  |
| 2              | FIELD_0001 | organic_carbon  | 12.5  | g/kg | 2026-01-01 | SoilGrids  |
| 3              | FIELD_0001 | rainfall        | 12.4  | mm   | 2024-06-01 | NASA POWER |
| 4              | FIELD_0001 | temperature_max | 32.1  | °C   | 2024-06-01 | NASA POWER |

These values are illustrative, not actual measurements.

The full table should have additional fields:

```
observation_id
field_id
variable_id
source_id
dataset_id
source_asset_id

value_numeric
value_text
original_value
original_unit
standardized_unit

observed_at
period_start
period_end

depth_top_cm
depth_bottom_cm

crop_id
cultivar_id
growth_stage_id

statistic
measurement_type
extraction_method

spatial_resolution_m
temporal_resolution
spatial_coverage_percent

uncertainty
quality_flag

processing_version
retrieved_at
created_at
```

Not every column will apply to every observation. For instance, soil depth is relevant for soil measurements but not annual rainfall.

We should therefore allow unused fields to remain null.

### **Measurement types**

Every value should have a classification:

| Classification | Example                                                |
| -------------- | ------------------------------------------------------ |
| `measured`     | Soil Health Card pH                                    |
| `satellite`    | Sentinel-2 NDVI                                        |
| `modelled`     | SoilGrids soil pH                                      |
| `reanalysis`   | ERA5-Land soil moisture                                |
| `derived`      | Water-holding capacity calculated from soil properties |
| `simulated`    | APSIM crop biomass                                     |
| `surveyed`     | Farmer-reported borewell reliability                   |

This prevents a simulated crop-growth value from being mistaken for an actual field observation.

### **Missing values**

We should distinguish:

- Not collected.
- Not available from source.
- Outside source coverage.
- Access restricted.
- Collection failed.
- Not applicable.
- Below detection limit.

Do not simply store zero.

## **6.3 Crop parameter database**

Crop parameters require a somewhat different structure from environmental observations.

A crop might have different minimum and maximum temperature requirements at different growth stages.

I recommend:

`crop_parameters`

| Column               | Example                      |
| -------------------- | ---------------------------- |
| crop_id              | CROP_001                     |
| cultivar_id          | VAR_001 or null              |
| variable_id          | temperature_optimum          |
| growth_stage_id      | flowering                    |
| minimum_value        | 20                           |
| optimum_value        | 28                           |
| maximum_value        | 35                           |
| unit                 | °C                           |
| geographical_context | Karnataka                    |
| source_id            | ICAR                         |
| evidence_type        | Experimental / published     |
| confidence           | Recorded assessment          |
| reference            | Study or document identifier |

This allows us to represent crop requirements correctly.

The same structure can support:

- Rainfall tolerance.
- pH tolerance.
- Salinity tolerance.
- Nutrient requirements.
- Germination conditions.
- Temperature response.
- Waterlogging tolerance.

## **6.4 Crop performance database**

Crop trials should have their own table because experimental conditions matter.

A trial record should include:

```
trial_id
crop_id
cultivar_id
field_or_trial_location
soil_conditions
weather_period
sowing_date
harvest_date
irrigation_treatment
fertilizer_treatment
replication_count
experimental_method
source_reference
```

The performance record should contain the measured outcomes:

```
trial_id
yield_kg_per_ha
biomass_kg_per_ha
germination_percentage
plant_survival_percentage
water_consumption
nutrient_uptake
harvest_index
observed_stress
```

Actual experimental results should remain distinct from DSSAT/APSIM simulated outputs.

## **6.5 Crop rotation database**

We need to record interactions between a preceding crop and a following crop.

For example:

```
previous_crop: CROP_A
following_crop: CROP_B

nitrogen_change: ...
soil_moisture_change: ...
organic_carbon_change: ...
residue_quantity: ...
decomposition_rate: ...
shared_diseases: ...
observed_yield_effect: ...

study_location: ...
soil_conditions: ...
study_duration: ...
source: ...
```

This lets us eventually compare multiple possible rotations on the same plot.

It is particularly important to preserve the conditions under which a rotation effect was observed. Nitrogen fixation, for example, is not one constant value for every legume in every soil.

# **7. Master data dictionary and unit standardization**

Before writing the acquisition pipeline, create `variables.yaml` or an equivalent database registry.

Every characteristic in Sections 2.1–2.16 should receive a canonical variable identifier.

Example:

```
soil_ph:
  category: soil
  description: Soil acidity or alkalinity
  unit: pH
  measurement_type:
    - measured
    - modelled
  temporal_type: observation
  depth_dependent: true

rainfall:
  category: climate
  description: Precipitation
  unit: mm
  measurement_type:
    - measured
    - satellite
    - reanalysis
  temporal_type: daily

ndvi:
  category: vegetation
  description: Normalized Difference Vegetation Index
  unit: dimensionless
  measurement_type:
    - satellite
    - derived
  temporal_type: observation

crop_temperature_optimum:
  category: crop_requirement
  description: Optimum temperature for a crop at a specific growth stage
  unit: degC
  stage_dependent: true
  cultivar_dependent: true
```

## **7.1 Recommended canonical units**

| Variable category      | Canonical unit                                 |
| ---------------------- | ---------------------------------------------- |
| Soil texture           | %                                              |
| Organic carbon         | g/kg or % with explicit conversion             |
| Soil pH                | Dimensionless                                  |
| Soil EC                | dS/m                                           |
| Soil nutrients         | mg/kg or kg/ha, depending on measurement basis |
| Soil bulk density      | g/cm³                                          |
| Soil depth             | cm                                             |
| Hydraulic conductivity | mm/hour or other explicitly recorded unit      |
| Soil moisture          | m³/m³                                          |
| Rainfall               | mm                                             |
| Rainfall intensity     | mm/hour                                        |
| Temperature            | °C                                             |
| Wind speed             | m/s                                            |
| Humidity               | %                                              |
| Solar radiation        | MJ/m²/day or W/m², with temporal support       |
| Elevation              | m                                              |
| Slope                  | Degrees or %                                   |
| Area                   | hectares                                       |
| Groundwater level      | m below ground level, with reference           |
| Water EC               | dS/m                                           |
| Yield                  | kg/ha                                          |
| Biomass                | kg/ha                                          |
| Water use              | mm or m³/ha                                    |
| Nitrogen fixation      | kg N/ha over a specified period                |
| GPP/NPP                | Product-defined carbon mass per area per time  |
| NDVI/EVI/NDMI          | Dimensionless                                  |
| Crop development       | Days after sowing or thermal time              |

Do not assume that two values with the same apparent unit have the same measurement basis. Available phosphorus in mg/kg and phosphorus fertilizer application in kg/ha are different quantities.

Every variable should also document its depth, time interval, sample method and spatial support where applicable.

# **8. Notebook-first implementation plan**

This is how I would actually build the project.

**We will implement and test the entire pipeline inside Jupyter notebooks first. Only after the acquisition, processing, calculations and storage are working will we refactor the functionality into reusable Python files.**

The notebooks should be educational and readable, not just places where we execute a large block of code.

Every notebook should explain:

1. What data we are collecting.
2. Why the data is useful.
3. Which source provides it.
4. How the data is retrieved.
5. What the response or downloaded dataset looks like.
6. How it is cleaned and normalized.
7. How the KML geometry is used.
8. How the data is calculated or extracted.
9. How the result is visualized.
10. How it is saved locally.
11. What the limitations are.

## **Phase 0 — Set up the development environment**

First implementation task

**Notebook:&#x20;**`00_project_overview.ipynb`

Explain the complete architecture, data domains, sources and project goals.

**Notebook:&#x20;**`01_environment_setup.ipynb`

Install and test the required packages:

```
pip install \
    jupyterlab \
    pandas \
    numpy \
    geopandas \
    shapely \
    pyogrio \
    rasterio \
    rioxarray \
    xarray \
    netCDF4 \
    requests \
    matplotlib \
    scipy \
    pyproj \
    rasterstats \
    earthengine-api \
    sqlalchemy \
    psycopg2-binary \
    geoalchemy2 \
    pyarrow \
    pyyaml \
    python-dotenv
```

Additional tools:

- PostgreSQL.
- PostGIS extension.
- GDAL system libraries.
- Google Earth Engine authentication.
- Copernicus CDS credentials if ERA5-Land is used.

**Expected result:** JupyterLab opens, dependencies import successfully, and the local database can be reached.

## **Phase 1 — KML ingestion and geospatial processing**

**Notebook:&#x20;**`02_kml_ingestion.ipynb`

Tasks:

1. Load the KML/KMZ file.
2. Inspect all placemarks.
3. Visualize the polygons.
4. Extract polygon names and identifiers.
5. Generate field IDs.
6. Check for invalid geometries.
7. Repair suitable invalid geometries.
8. Calculate area and perimeter.
9. Calculate centroids.
10. Export to GeoJSON and GeoPackage.

**Notebook:&#x20;**`03_geospatial_processing.ipynb`

Tasks:

1. Investigate source coordinate systems.
2. Reproject geometries where needed.
3. Generate field bounding boxes.
4. Create optional surrounding buffers.
5. Calculate intersections with sample rasters.
6. Test zonal statistics.
7. Verify pixel coverage and spatial resolution.
8. Test geometry-based source selection.

**Phase 1 expected output**

Example local files

```
data/processed/fields/
    fields.geojson
    fields.gpkg
    field_metadata.parquet
```

A usable field database with stable identifiers, valid geometries and area calculations.

A simple initial KML-reading implementation would look like:

```
import geopandas as gpdkml_path = "farm_area.kml"fields = gpd.read_file(kml_path, driver="KML")if fields.crs is None:    raise ValueError("The KML has no recognized CRS")fields = fields.to_crs("EPSG:4326")fields["geometry"] = fields.geometry.make_valid()fields = fields[    fields.geometry.geom_type.isin(        ["Polygon", "MultiPolygon"]    )].copy()fields["field_id"] = [    f"FIELD_{i:04d}"    for i in range(1, len(fields) + 1)]# Equal-area projection for area calculations.area_fields = fields.to_crs("EPSG:6933")fields["area_ha"] = (    area_fields.geometry.area / 10_000)
```

This is only the initial example; production handling must also preserve the original feature IDs, handle multiple polygons inside folders, deal with reader compatibility and validate geometries before assigning final IDs.

## **Phase 2 — Source registry and environmental acquisition**

**Notebook:&#x20;**`04_source_registry.ipynb`

Create the first inventory of sources and variables.

For each source, test:

- Is the source reachable?
- Does it provide the requested variable?
- What dates are available?
- What is its resolution?
- Does it require authentication?
- What format does it return?
- Are there rate or licensing limitations?

Do not download huge datasets just to test whether an endpoint works.

### **Notebook:&#x20;**`05_soil_data.ipynb`

Implementation:

1. Select fields from the KML.
2. Query SoilGrids.
3. Inspect the original response.
4. Extract soil properties and depths.
5. Normalize units.
6. Map values to the variable registry.
7. Compare against available Soil Health Card results.
8. Save original and processed records.
9. Visualize soil-property distributions.

Expected data:

- Texture.
- Soil pH.
- Organic carbon.
- Nitrogen.
- Bulk density.
- CEC.
- Coarse fragments.
- Available depth profiles.

Document which characteristics are missing and require further data sources.

### **Notebook:&#x20;**`06_climate_data.ipynb`

Implementation:

1. Use the KML to obtain representative query coordinates.
2. Query NASA POWER.
3. Retrieve daily records.
4. Parse and normalize the JSON response.
5. Retrieve rainfall data from an additional source when available.
6. Preserve the original daily records.
7. Store records against field IDs.

Parameters to initially test:

```
PRECTOTCORR
T2M
T2M_MAX
T2M_MIN
RH2M
```

### **Notebook:&#x20;**`07_climate_indicators.ipynb`

Calculate:

- Annual rainfall.
- Monthly rainfall.
- Rainy-day count.
- Growing-season rainfall.
- Longest dry spell.
- Rainfall anomalies.
- SPI.
- SPEI.
- Temperature averages.
- Heatwave frequency.
- Growing degree days.
- Vapour pressure deficit.
- Reference evapotranspiration.

Visualizations should include rainfall time series, monthly precipitation distributions, temperature distributions and dry-spell history.

### **Notebook:&#x20;**`08_terrain_geology.ipynb`

Retrieve:

- Elevation.
- Slope.
- Aspect.
- Curvature.
- Topographic wetness index.
- Flow accumulation.
- Watershed membership.
- Geological and geomorphological classifications.

Calculate terrain-derived variables from the DEM rather than attempting to obtain a separate API for every derived property.

### **Notebook:&#x20;**`09_water_data.ipynb`

Retrieve or import:

- CGWB monitoring well records.
- Groundwater levels.
- Groundwater trends.
- Aquifer information.
- Nearby surface-water features.
- SMAP soil moisture.
- ERA5-Land root-zone soil moisture.
- Reservoir and canal information where available.

Add structured import templates for:

- Water EC.
- Water pH.
- TDS.
- SAR.
- Borewell reliability.
- Irrigation access.

### **Notebook:&#x20;**`10_satellite_data.ipynb`

Set up Earth Engine and retrieve sample data.

Initially test:

- Sentinel-2.
- Landsat.
- MODIS.
- Sentinel-1.
- ESA WorldCover.
- Dynamic World.
- JRC Global Surface Water.

Test filtering by the KML geometry and date range.

### **Notebook:&#x20;**`11_vegetation_indices.ipynb`

Calculate:

\\[ NDVI=\frac{NIR-Red}{NIR+Red} \\]

\\[ NDMI=\frac{NIR-SWIR}{NIR+SWIR} \\]

\\[ SAVI=\frac{(NIR-Red)(1+L)}{NIR+Red+L} \\]

Also investigate:

- EVI.
- LAI.
- fAPAR.
- Vegetation anomalies.
- Seasonal growth patterns.
- Historical phenology.

Use consistent cloud masking and quality filtering before creating time series.

## **Phase 3 — Crop data acquisition**

These notebooks collect data that is associated with crop species and cultivars, rather than directly extracted from an environmental raster.

### **Notebook:&#x20;**`12_crop_requirements.ipynb`

Sources:

- EcoCrop.
- GAEZ.
- ICAR.
- DSSAT.
- APSIM.
- UAS Bengaluru.
- UAS Dharwad.

Import requirements for each crop:

- Temperature.
- Rainfall.
- pH.
- Soil texture.
- Depth.
- Drainage.
- Nutrients.
- Salinity.
- Altitude.
- Growing period.
- Photoperiod.
- Light.

The output should be one structured crop profile per species/cultivar, with documented sources.

### **Notebook:&#x20;**`13_germination_development.ipynb`

Retrieve or import:

- Germination requirements.
- Emergence.
- Seedling survival.
- Root growth.
- Growth stages.
- LAI curves.
- Biomass accumulation.
- Flowering.
- Pollination.
- Grain formation.
- Maturity.
- Harvest index.
- Water-use efficiency.
- Nutrient-use efficiency.

Build time-series plots for crop development parameters where observations are available.

### **Notebook:&#x20;**`14_crop_performance.ipynb`

Import:

- Historical crop yield.
- Production.
- Cultivated area.
- Crop failure.
- Yield variations.
- Cultivar performance.
- Stress-response experimental data.

Make a clear separation between national/state/district statistical records and plot-level trial results.

### **Notebook:&#x20;**`15_biological_risks.ipynb`

Import:

- Pest-host relationships.
- Disease-host relationships.
- Pathogens.
- Root diseases.
- Fungal, bacterial and viral diseases.
- Weed competition information.
- Pollinator requirements.

Organize pests and diseases using standardized identities, scientific names, affected crops and available source references.

### **Notebook:&#x20;**`16_crop_rotation.ipynb`

Import:

- Nitrogen fixation.
- NPK uptake.
- Nutrient depletion and replenishment.
- Crop residues.
- Residue decomposition.
- Root contribution.
- Organic matter changes.
- Soil structure changes.
- Water consumption.
- Soil moisture carryover.
- Allelopathy.
- Shared biological risks.
- Crop family compatibility.
- Rotation interval recommendations.

Run initial APSIM/DSSAT example simulations only after the necessary crop, soil, weather and management inputs are available.

### **Notebook:&#x20;**`17_cultivation_management.ipynb`

Create structured import forms and datasets for:

- Crop variety.
- Sowing and harvesting dates.
- Seed quality.
- Seed rate.
- Plant population.
- Row spacing.
- Irrigation schedule and volume.
- Fertilizer applications.
- Tillage.
- Weed management.
- Pest management.
- Residue management.
- Harvesting method.

### **Notebook:&#x20;**`18_sensor_data.ipynb`

Build common import formats for:

- Weather stations.
- Soil probes.
- Leaf wetness.
- Flow meters.
- Plant tissue laboratory results.
- PAR and LAI instruments.

All sensor records must be associated with a field, sensor, installation position, measurement depth if relevant and timestamp.

Pasted text(5).txt

## **Phase 4 — Database integration and end-to-end testing**

### **Notebook:&#x20;**`19_database_integration.ipynb`

Create the PostgreSQL/PostGIS database and table structures.

Implement:

1. Field import.
2. Source registry import.
3. Variable registry import.
4. Raw asset registration.
5. Environmental observation insertion.
6. Crop parameter insertion.
7. Crop trial insertion.
8. Rotation and management insertion.
9. Duplicate detection.
10. Database querying.

Verify that every observation can be traced back to its source file or retrieval job.

### **Notebook:&#x20;**`20_end_to_end_test.ipynb`

This is the first complete project demonstration.

Input:

```
farm_area.kml
```

Output:

```
FIELD_0001

Soil:
    Retrieved soil properties
    Depth-specific estimates

Climate:
    Historical daily records
    Monthly and annual indicators

Water:
    Groundwater context
    Historical soil moisture

Historical land:
    NDVI time series
    Vegetation indices

Crop:
    Requirements database
    Growth parameters
    Performance records
    Biological risks

Rotation:
    Nutrient effects
    Residue effects
    Crop compatibility
```

The test should verify that data retrieval, processing, database storage and exports work together.

# **9. Converting the notebooks into Python files**

Only after notebook validation

Once each notebook has been tested and its outputs are correct, we refactor its working code into Python modules.

The notebooks remain in the project permanently.

They serve as the explanation and demonstration layer. Python files become the reusable implementation layer.

**Do not delete the notebooks after conversion.**

## **9.1 Proposed Python package**

```
src/
└── agri_data/
    │
    ├── __init__.py
    ├── config.py
    │
    ├── geo/
    │   ├── __init__.py
    │   ├── kml.py
    │   ├── geometry.py
    │   ├── area.py
    │   ├── buffers.py
    │   ├── stations.py
    │   └── zonal_statistics.py
    │
    ├── sources/
    │   ├── __init__.py
    │   ├── soilgrids.py
    │   ├── soil_health_card.py
    │   ├── nasa_power.py
    │   ├── ksndmc.py
    │   ├── imd.py
    │   ├── chirps.py
    │   ├── era5_land.py
    │   ├── cgwb.py
    │   ├── india_wris.py
    │   ├── gee.py
    │   ├── faostat.py
    │   ├── ecocrop.py
    │   ├── gaez.py
    │   ├── dssat.py
    │   └── apsim.py
    │
    ├── processing/
    │   ├── __init__.py
    │   ├── soil.py
    │   ├── climate.py
    │   ├── drought.py
    │   ├── terrain.py
    │   ├── hydrology.py
    │   ├── vegetation.py
    │   ├── crop_classification.py
    │   ├── unit_conversion.py
    │   └── quality_control.py
    │
    ├── crop/
    │   ├── __init__.py
    │   ├── catalog.py
    │   ├── requirements.py
    │   ├── development.py
    │   ├── performance.py
    │   ├── biological_risks.py
    │   └── cultivation.py
    │
    ├── rotation/
    │   ├── __init__.py
    │   ├── nutrient_cycling.py
    │   ├── residue.py
    │   ├── moisture.py
    │   ├── compatibility.py
    │   └── sequence.py
    │
    ├── storage/
    │   ├── __init__.py
    │   ├── database.py
    │   ├── assets.py
    │   ├── observations.py
    │   └── exports.py
    │
    └── pipeline/
        ├── __init__.py
        ├── acquisition.py
        ├── extraction.py
        └── orchestration.py
```

Not every listed file needs to be created immediately. Some may be grouped together until their functionality is sufficiently large.

## **9.2 Notebook-to-Python mapping**

| Notebook                 | Python module                                    |
| ------------------------ | ------------------------------------------------ |
| 02 KML ingestion         | `geo/kml.py`                                     |
| 03 Geospatial processing | `geo/geometry.py`, `geo/zonal_statistics.py`     |
| 05 Soil                  | `sources/soilgrids.py`, `processing/soil.py`     |
| 06 Climate               | `sources/nasa_power.py`                          |
| 07 Climate indicators    | `processing/climate.py`, `processing/drought.py` |
| 08 Terrain               | `processing/terrain.py`                          |
| 09 Water                 | `sources/cgwb.py`, `processing/hydrology.py`     |
| 10 Satellite             | `sources/gee.py`                                 |
| 11 Vegetation            | `processing/vegetation.py`                       |
| 12 Crop requirements     | `crop/requirements.py`                           |
| 13 Crop development      | `crop/development.py`                            |
| 14 Crop performance      | `crop/performance.py`                            |
| 15 Biological risks      | `crop/biological_risks.py`                       |
| 16 Rotation              | `rotation/`                                      |
| 17 Management            | `crop/cultivation.py`                            |
| 19 Database              | `storage/`                                       |
| 20 Integration           | `pipeline/orchestration.py`                      |

## **9.3 How the notebooks should work after conversion**

For example, once the SoilGrids notebook has been validated, the actual querying logic moves into:

```
src/agri_data/sources/soilgrids.py
```

The notebook then becomes a readable demonstration:

```
# 1. Import the working implementation.from agri_data.sources.soilgrids import SoilGridsClient# 2. Load selected field geometries.from agri_data.geo.kml import load_fieldsfields = load_fields("farm_area.kml")# 3. Initialize the data source.client = SoilGridsClient()# 4. Retrieve soil data.soil_data = client.retrieve(fields)# 5. Display and inspect results.display(soil_data.head())# 6. Visualize the results.soil_data.plot()
```

The actual implementation is maintained once in the Python package, while the notebook explains how and why it works.

# **10. Acquisition orchestration: how the complete system should operate**

Eventually, we need one command or interface that ties everything together.

It should behave approximately like this:

```
User supplies KML
       |
       v
Load and validate polygons
       |
       v
Create / identify field IDs
       |
       v
Read acquisition configuration
       |
       v
Determine source coverage
       |
       v
Download required source data
       |
       v
Cache original files
       |
       v
Extract data by polygon
       |
       v
Normalize units and formats
       |
       v
Calculate derived variables
       |
       v
Run quality checks
       |
       v
Save observations to database
       |
       v
Export agricultural plot profiles
```

## **10.1 Configuration-driven collection**

We should not hardcode all the data collection settings into the Python files.

Instead, use a project configuration file.

Example:

```
project:
  name: Karnataka Agriculture Data
  region: Karnataka

input:
  kml_path: data/input/farm_area.kml

acquisition:
  soil:
    enabled: true

  climate:
    enabled: true
    start_date: "2015-01-01"
    end_date: "2026-01-01"

  terrain:
    enabled: true

  water:
    enabled: true

  historical_land:
    enabled: true

  crop_data:
    enabled: true

processing:
  calculate_zonal_statistics: true
  calculate_ndvi: true
  calculate_ndmi: true
  calculate_drought_indices: true

storage:
  database: postgresql
  save_raw: true
  save_processed: true
  save_derived: true
```

Those dates are example configuration values, not assertions that every source covers the full period.

We should also support a smaller test configuration so the first few notebook runs do not download years of satellite imagery.

## **10.2 Source adapters**

Every source should eventually provide a consistent interface.

Conceptually:

```
class DataSource:    def retrieve(        self,        geometry,        variables,        start_date=None,        end_date=None    ):        pass    def process(self, raw_data):        pass    def validate(self, processed_data):        pass    def save(self, data):        pass
```

Actual APIs can behave differently internally, but the rest of the system should not need to understand those differences.

For example, NASA POWER, SoilGrids and Earth Engine can all be called through their own source adapters.

The output of each adapter should have standardized metadata and variable identifiers.

## **10.3 Caching and repeat runs**

An important performance feature is avoiding unnecessary repeat downloads.

Suppose you upload two KMLs that contain nearby farms.

The satellite imagery may be identical for both.

We should:

- Download imagery once.
- Save its original scene identifier and file.
- Cache processed tiles.
- Extract statistics separately for each field.
- Reuse existing data when its version, time period and spatial coverage are still valid.
- Re-download when the source is updated or the requested coverage is incomplete.

Every retrieval should generate an `extraction_job_id`.

This gives us a record of what ran, which fields were included, which datasets were retrieved and which failed.

# **11. Quality control and validation**

We should not consider the system successful just because an API returned a response.

The data must be usable and scientifically interpretable.

| Validation                | What to check                                                      |
| ------------------------- | ------------------------------------------------------------------ |
| Geometry validation       | Are field boundaries valid?                                        |
| Coordinate validation     | Are points within the expected region?                             |
| API validation            | Did the source return the expected variables?                      |
| Unit validation           | Are values converted correctly?                                    |
| Date validation           | Are there missing or duplicated days?                              |
| Raster validation         | Do the pixels intersect the actual polygon?                        |
| Coverage validation       | What percentage of the field has valid data?                       |
| Resolution validation     | Is the source resolution adequate for the intended interpretation? |
| Physical range validation | Are measurements physically plausible?                             |
| Provenance validation     | Can every result be traced back to its source?                     |
| Statistical validation    | Are aggregates calculated correctly?                               |
| Cross-source validation   | Do independent datasets broadly agree?                             |

### **Cross-validation examples**

For rainfall:

- Compare KSNDMC station observations.
- Compare NASA POWER.
- Compare CHIRPS.
- Compare GPM where suitable.

For soil:

- Compare SoilGrids.
- Compare Soil Health Card laboratory values.
- Record depth differences and sampling dates.

For vegetation:

- Compare Landsat and Sentinel-2 trends during overlapping periods.
- Check cloud coverage.
- Compare vegetation changes with farmer-reported crop history.

For water:

- Compare SMAP or ERA5-Land estimates with field soil moisture probes.
- Compare groundwater estimates against available CGWB wells.

Never force values to agree simply because we expect them to. Discrepancies should be retained and investigated.

# **12. Final implementation roadmap and priorities**

I would implement the project in the following order.

| Stage | Main deliverable              | Completion condition                                        |
| ----- | ----------------------------- | ----------------------------------------------------------- |
| 1     | Environment and project setup | JupyterLab, dependencies and database work                  |
| 2     | KML ingestion                 | Multiple plots correctly identified and stored              |
| 3     | SoilGrids integration         | Soil profile retrieved and extracted                        |
| 4     | NASA POWER integration        | Historical daily weather stored                             |
| 5     | Climate indicators            | Rainfall, dry spells and temperature metrics calculated     |
| 6     | Terrain integration           | DEM and terrain characteristics extracted                   |
| 7     | Water integration             | Available groundwater and soil moisture datasets integrated |
| 8     | Satellite integration         | Sentinel/Landsat time series extracted                      |
| 9     | Crop requirement database     | Crop parameters structured by stage and cultivar            |
| 10    | Crop development database     | Germination and growth parameters imported                  |
| 11    | Performance database          | Historical results and trials stored                        |
| 12    | Biological risk database      | Crop-pest-disease relationships structured                  |
| 13    | Rotation database             | Nutrient and crop interaction data represented              |
| 14    | Management database           | Field cultivation records imported                          |
| 15    | Full integration              | KML generates a complete agricultural data profile          |
| 16    | Python refactoring            | Notebook logic migrated into reusable modules               |
| 17    | Pipeline validation           | Repeatable runs with tests and provenance                   |

## **12.1 What should be in the first working prototype?**

I would deliberately keep the first prototype small enough that we can verify every result.

## **Prototype 1 — KML to agricultural environmental profile**

Initial milestone

**Input**

One KML file containing multiple agricultural plots.

**Data acquisition**

- SoilGrids.
- NASA POWER.
- DEM data.
- Sentinel-2.

**Processing**

- Polygon extraction.
- Soil profile retrieval.
- Historical rainfall and temperature.
- Terrain calculations.
- NDVI time series.

**Local storage**

- PostgreSQL/PostGIS.
- Raw JSON.
- GeoTIFF.
- Parquet.
- JSON field profiles.

**Output**

One standardized environmental profile per field, with source, resolution, date and measurement-type metadata.

After this works, we expand into groundwater, crop requirements, crop growth, performance, biological risks, rotation effects and cultivation data.

# **13. The specific development sequence I recommend**

There is one thing I would avoid: starting with all 20 notebooks at once.

Instead, build and validate in small groups.

## **First development sprint**

Notebook implementation order

1. **00 — Project overview**

   Document system architecture and data domains.
2. **01 — Environment setup**

   Install libraries, configure Jupyter and connect PostGIS.
3. **02 — KML ingestion**

   Read, validate and visualize your actual farm polygons.
4. **03 — Geospatial processing**

   Test intersections, buffers, area and zonal statistics.
5. **04 — Source registry**

   Establish the actual variables and source acquisition methods.
6. **05 — SoilGrids**

   Retrieve the first real environmental dataset and save it locally.
7. **19 — Database integration**

   Store and retrieve the first field profile from PostGIS.

**First milestone achieved when:**

You upload a KML, run the notebooks, retrieve soil data for every field, and can query the resulting records from your local database.

Then we continue with climate, terrain, water and satellite data before moving into crop-specific datasets.

## **14. Important technical decisions to preserve throughout the project**

I would establish these as permanent project rules:

1. **Every field must have a stable ID.** All datasets use that ID to connect observations to the plot.
2. **Every value must have provenance.** Store where it came from and how it was obtained.
3. **Never overwrite the original data.** Keep raw, normalized and derived data separate.
4. **Keep depth and time dimensions.** Soil properties depend on depth, and weather and crop growth depend on time.
5. **Do not fabricate missing data.** Missing, unavailable and zero are different.
6. **Preserve spatial resolution.** Do not claim a coarse dataset provides field-level precision.
7. **Keep measured and modelled values separate.**
8. **Version datasets and processing methods.** Reprocessing must be reproducible.
9. **Keep crop requirements separate from environmental observations.** One describes what a crop needs, and the other describes what a field provides.
10. **Keep crop performance separate from crop requirements.** A theoretical tolerance is not proof of successful cultivation.
11. **Keep cultivation records separate from environmental measurements.** Management materially affects the outcome.
12. **Make acquisition repeatable.** Running the same KML and configuration again should not create duplicate observations or unnecessary downloads.

## **15. Final project structure**

Our development will progress through three distinct deliverables:

Deliverable 1

**Jupyter research and data acquisition system**

All data sources tested, their responses understood, spatial processing developed, visualizations created and outputs locally stored.

Purpose: human-readable development, experimentation and validation.

Deliverable 2

**Reusable Python data platform**

Validated notebook code refactored into source adapters, geospatial utilities, processing functions, database interfaces and a central pipeline.

Purpose: repeatable and maintainable data collection.

Deliverable 3

**Agricultural data foundation for modelling**

A complete collection of plot environmental profiles, crop requirements, development parameters, historical performance, management history and crop-rotation interactions.

Purpose: future crop-suitability and crop-rotation algorithms.

**My recommendation is to make the first concrete deliverable the notebook-based KML → SoilGrids → PostGIS workflow.** It tests the core architecture: geographical selection, external acquisition, polygon-based extraction, data normalization and local persistence. Once that works, every additional source can use the same framework rather than requiring a new system.