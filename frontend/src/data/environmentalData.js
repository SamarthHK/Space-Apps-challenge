/**
 * Karnataka Agro-Climatic & Satellite Earth Observation Baseline
 * Pilot Districts: Tumakuru (Southern Dry Zone) & Mandya (Southern Transition / Kaveri Basin)
 * Data Sources: KSNDMC (Karnataka State Natural Disaster Monitoring Centre), IMD, ESA Copernicus Sentinel-2
 */

export const districtClimateBaselines = {
  Tumakuru: {
    district: "Tumakuru",
    state: "Karnataka",
    agroZone: "Zone 4 — Southern Dry Zone",
    annualRainfallMm: 688,
    kharifRainfallMm: 375,
    rabiRainfallMm: 165,
    summerRainfallMm: 148,
    avgDrySpellsKharif: "2 to 3 spells (duration 12-18 days)",
    droughtVulnerability: "Moderate to High (Dryland dependency)",
    groundwaterStatus: "Semi-critical to Over-exploited in Eastern Taluks (Pavagada, Koratagere, Madhugiri)",
    monthlyRainfallNormalMm: [
      { month: "Jan", rainfallMm: 2, tempMaxC: 30.1, tempMinC: 15.2 },
      { month: "Feb", rainfallMm: 4, tempMaxC: 32.8, tempMinC: 17.1 },
      { month: "Mar", rainfallMm: 11, tempMaxC: 35.6, tempMinC: 20.2 },
      { month: "Apr", rainfallMm: 42, tempMaxC: 37.0, tempMinC: 22.4 },
      { month: "May", rainfallMm: 85, tempMaxC: 36.2, tempMinC: 22.8 },
      { month: "Jun", rainfallMm: 68, tempMaxC: 32.5, tempMinC: 21.6 },
      { month: "Jul", rainfallMm: 79, tempMaxC: 30.8, tempMinC: 21.2 },
      { month: "Aug", rainfallMm: 92, tempMaxC: 30.2, tempMinC: 20.8 },
      { month: "Sep", rainfallMm: 136, tempMaxC: 30.7, tempMinC: 20.7 }, // Peak monsoon
      { month: "Oct", rainfallMm: 118, tempMaxC: 30.1, tempMinC: 20.3 },
      { month: "Nov", rainfallMm: 41, tempMaxC: 29.2, tempMinC: 18.2 },
      { month: "Dec", rainfallMm: 10, tempMaxC: 28.6, tempMinC: 15.8 }
    ],
    soilTypesDominant: ["Red sandy loam (72%)", "Black clay loam in valleys (18%)", "Gravelly lateritic (10%)"]
  },

  Mandya: {
    district: "Mandya",
    state: "Karnataka",
    agroZone: "Zone 6 — Southern Transition Zone / Kaveri Command",
    annualRainfallMm: 706,
    kharifRainfallMm: 310,
    rabiRainfallMm: 240,
    summerRainfallMm: 156,
    avgDrySpellsKharif: "1 to 2 spells (buffer provided by VC canal)",
    droughtVulnerability: "Low in Canal command; Moderate in rainfed Malavalli/Nagamangala",
    groundwaterStatus: "Safe to Semi-critical; high recharge along canal distributaries",
    monthlyRainfallNormalMm: [
      { month: "Jan", rainfallMm: 3, tempMaxC: 29.8, tempMinC: 15.6 },
      { month: "Feb", rainfallMm: 5, tempMaxC: 32.4, tempMinC: 17.5 },
      { month: "Mar", rainfallMm: 14, tempMaxC: 35.0, tempMinC: 20.5 },
      { month: "Apr", rainfallMm: 55, tempMaxC: 36.1, tempMinC: 22.6 },
      { month: "May", rainfallMm: 96, tempMaxC: 34.8, tempMinC: 22.5 },
      { month: "Jun", rainfallMm: 52, tempMaxC: 31.4, tempMinC: 21.5 },
      { month: "Jul", rainfallMm: 60, tempMaxC: 29.8, tempMinC: 21.0 },
      { month: "Aug", rainfallMm: 78, tempMaxC: 29.5, tempMinC: 20.8 },
      { month: "Sep", rainfallMm: 120, tempMaxC: 30.2, tempMinC: 20.5 },
      { month: "Oct", rainfallMm: 154, tempMaxC: 29.7, tempMinC: 20.0 }, // North-East monsoon peak
      { month: "Nov", rainfallMm: 58, tempMaxC: 28.9, tempMinC: 18.0 },
      { month: "Dec", rainfallMm: 11, tempMaxC: 28.2, tempMinC: 15.9 }
    ],
    soilTypesDominant: ["Red sandy loam (55%)", "Alluvial clay loam (35%)", "Deep black soil (10%)"]
  }
};

/**
 * Satellite Earth Observation Passes History
 * Modeled after ESA Sentinel-2 MSI & Landsat 8/9 Level-2A BOA (Bottom-Of-Atmosphere)
 * Matches the reference GUI imagery pass calendar card
 */
export const satellitePassesHistory = [
  {
    id: "pass-2026-11-12",
    date: "2026-11-12",
    dateFormatted: "12 Nov 2026",
    satellite: "Sentinel-2B",
    resolution: "10m MSI Multi-Spectral",
    cloudCoverPct: 2,
    meanNdvi: 0.74,
    minNdvi: 0.28,
    maxNdvi: 0.88,
    meanNdwi: 0.18, // Water stress index
    canopyStatus: "Vigorous Active Canopy (Post-monsoon grain filling)",
    canopyInterpretation: "Crop leaves are dense and actively photosynthesizing. Low water stress.",
    selected: true
  },
  {
    id: "pass-2026-11-02",
    date: "2026-11-02",
    dateFormatted: "02 Nov 2026",
    satellite: "Sentinel-2A",
    resolution: "10m MSI Multi-Spectral",
    cloudCoverPct: 8,
    meanNdvi: 0.71,
    minNdvi: 0.25,
    maxNdvi: 0.84,
    meanNdwi: 0.22,
    canopyStatus: "Dense Vegetative Cover",
    canopyInterpretation: "Uniform canopy growth across plot; vegetative peak.",
    selected: false
  },
  {
    id: "pass-2026-10-23",
    date: "2026-10-23",
    dateFormatted: "23 Oct 2026",
    satellite: "Landsat 9",
    resolution: "30m OLI-2",
    cloudCoverPct: 15,
    meanNdvi: 0.65,
    minNdvi: 0.22,
    maxNdvi: 0.79,
    meanNdwi: 0.26,
    canopyStatus: "Early Flowering / Canopy Closure",
    canopyInterpretation: "Crop rows closed, rapid biomass accumulation.",
    selected: false
  },
  {
    id: "pass-2026-10-08",
    date: "2026-10-08",
    dateFormatted: "08 Oct 2026",
    satellite: "Sentinel-2B",
    resolution: "10m MSI Multi-Spectral",
    cloudCoverPct: 75,
    meanNdvi: 0.58,
    minNdvi: 0.19,
    maxNdvi: 0.72,
    meanNdwi: 0.35,
    canopyStatus: "Partial Cloud Obscuration",
    canopyInterpretation: "High monsoon cloud cover; optical data partially obscured.",
    selected: false
  },
  {
    id: "pass-2026-09-18",
    date: "2026-09-18",
    dateFormatted: "18 Sep 2026",
    satellite: "Sentinel-2A",
    resolution: "10m MSI Multi-Spectral",
    cloudCoverPct: 5,
    meanNdvi: 0.44,
    minNdvi: 0.16,
    maxNdvi: 0.59,
    meanNdwi: 0.12,
    canopyStatus: "Seedling Tillering Stage",
    canopyInterpretation: "Young crops emerging; significant bare soil visible between rows.",
    selected: false
  },
  {
    id: "pass-2026-08-14",
    date: "2026-08-14",
    dateFormatted: "14 Aug 2026",
    satellite: "Sentinel-2B",
    resolution: "10m MSI Multi-Spectral",
    cloudCoverPct: 4,
    meanNdvi: 0.21,
    minNdvi: 0.12,
    maxNdvi: 0.28,
    meanNdwi: -0.05,
    canopyStatus: "Ploughed / Fallow Soil",
    canopyInterpretation: "Field was prepared and ploughed prior to Kharif sowing.",
    selected: false
  }
];

/**
 * Historical NDVI & Weather Time-Series for Bottom Drawer Graph
 * Matches the reference model's bottom multi-curve time-series graph
 */
export const ndviTimeSeriesData = [
  { date: "Aug 01", cloudPct: 10, mean: 0.18, median: 0.17, min: 0.12, max: 0.24, rainfallMm: 12 },
  { date: "Aug 15", cloudPct: 5,  mean: 0.22, median: 0.21, min: 0.14, max: 0.29, rainfallMm: 28 },
  { date: "Sep 01", cloudPct: 20, mean: 0.35, median: 0.33, min: 0.16, max: 0.48, rainfallMm: 45 },
  { date: "Sep 15", cloudPct: 8,  mean: 0.46, median: 0.45, min: 0.20, max: 0.58, rainfallMm: 62 },
  { date: "Oct 01", cloudPct: 40, mean: 0.59, median: 0.58, min: 0.24, max: 0.72, rainfallMm: 85 },
  { date: "Oct 15", cloudPct: 12, mean: 0.68, median: 0.67, min: 0.26, max: 0.81, rainfallMm: 34 },
  { date: "Nov 01", cloudPct: 6,  mean: 0.73, median: 0.72, min: 0.27, max: 0.86, rainfallMm: 14 },
  { date: "Nov 15", cloudPct: 2,  mean: 0.75, median: 0.74, min: 0.28, max: 0.89, rainfallMm: 2 }
];
