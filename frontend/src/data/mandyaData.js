/**
 * Mandya District, Karnataka, India — Agricultural Geospatial Dataset
 * Focus: Kaveri Basin, Visvesvaraya Canal Command Area, Sugarcane, Paddy, & Sericulture
 */

export const mandyaDistrictGeoJSON = {
  type: "FeatureCollection",
  features: [
    // 1. Mandya Central & VC Farm (Sugarcane & Paddy Core)
    {
      type: "Feature",
      id: "mandya-central",
      properties: {
        name: "Mandya Central & VC Canal Command",
        taluk: "Mandya",
        district: "Mandya",
        state: "Karnataka",
        country: "India",
        cropTypeSummary: "Sugarcane (Kabbu) & Sona Masuri Paddy",
        primaryCrops: ["Sugarcane (Co 86032 / Co 62175)", "Paddy (IR 64 / Sona Masuri)", "Mulberry (Sericulture)"],
        category: "sugar_paddy",
        areaHectares: 48500,
        ndviMean: 0.81,
        ndviColor: "#15803d",
        soilType: "Red Sandy Loam (Kavalu) & Clayey Alluvium",
        soilPh: 6.8,
        irrigationSource: "Visvesvaraya Canal (VC Canal) from KRS Dam",
        irrigationCoverage: "94% Canal & Borewell recharge",
        croppingSeasons: "Kharif (Jun-Nov), Rabi (Nov-Feb), Summer (Feb-May)",
        annualRainfallMm: 706,
        sugarRecoveryRate: "10.2% (Mysore Sugar Co. / MySugar Mill)",
        projectedYield: "105 t/ha (Sugarcane) / 5.8 t/ha (Paddy)",
        groundwaterDepthMeters: "12-18m",
        remoteSensingSource: "ISRO Bhuvan / Sentinel-2 MSI 10m",
        flyTo: { lat: 12.523, lng: 76.898, zoom: 12 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [76.80, 12.58],
            [76.96, 12.60],
            [77.02, 12.52],
            [76.97, 12.44],
            [76.82, 12.45],
            [76.78, 12.52],
            [76.80, 12.58]
          ]
        ]
      }
    },

    // 2. Pandavapura & French Rocks (Sugar Mills & Kaveri Riverfront)
    {
      type: "Feature",
      id: "pandavapura-sugar",
      properties: {
        name: "Pandavapura Sugar Agro-Zone",
        taluk: "Pandavapura",
        district: "Mandya",
        state: "Karnataka",
        country: "India",
        cropTypeSummary: "Perennial Sugarcane & Jaggery (Alepane) Belt",
        primaryCrops: ["Sugarcane", "Semi-dry Paddy", "Tender Coconut", "Banana"],
        category: "sugar_paddy",
        areaHectares: 34200,
        ndviMean: 0.84,
        ndviColor: "#15803d",
        soilType: "Deep Red Loam & Riverine Silt",
        soilPh: 7.1,
        irrigationSource: "Pandavapura Branch Canal & Lokapavani River",
        irrigationCoverage: "96% Perennial Gravity Flow",
        croppingSeasons: "Annual Sugarcane / Double-cropped Paddy",
        annualRainfallMm: 690,
        sugarRecoveryRate: "10.5% (Pandavapura Sahakari Sakkare Karkhane)",
        projectedYield: "115 t/ha (Sugarcane) / 6.1 t/ha (Paddy)",
        groundwaterDepthMeters: "8-14m",
        remoteSensingSource: "ISRO Cartosat-3 / Sentinel-2",
        flyTo: { lat: 12.502, lng: 76.668, zoom: 12 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [76.58, 12.56],
            [76.72, 12.58],
            [76.75, 12.48],
            [76.65, 12.42],
            [76.56, 12.47],
            [76.58, 12.56]
          ]
        ]
      }
    },

    // 3. Srirangapatna River Island & Delta (Intensive Paddy & Horticulture)
    {
      type: "Feature",
      id: "srirangapatna-delta",
      properties: {
        name: "Srirangapatna Kaveri Island Basin",
        taluk: "Srirangapatna",
        district: "Mandya",
        state: "Karnataka",
        country: "India",
        cropTypeSummary: "Heritage Wet Paddy, Betel Vine & Banana Groves",
        primaryCrops: ["Fine Sona Masuri Paddy", "Elakki Banana", "Betel Leaf (Veelyada Yele)", "Floriculture"],
        category: "horticulture",
        areaHectares: 28900,
        ndviMean: 0.86,
        ndviColor: "#15803d",
        soilType: "Rich Riverine Alluvium (Kaveri Delta Sediments)",
        soilPh: 6.9,
        irrigationSource: "North & South Kaveri Channels, Virija Canal",
        irrigationCoverage: "100% River channels & Inundation",
        croppingSeasons: "Tri-annual rotation (Paddy - Pulses - Vegetables)",
        annualRainfallMm: 720,
        sugarRecoveryRate: "N/A (Primarily Food & Cash Crops)",
        projectedYield: "6.5 t/ha (Premium Rice) / 38 t/ha (Banana)",
        groundwaterDepthMeters: "4-9m (High Water Table)",
        remoteSensingSource: "Copernicus Sentinel-2 10m L2A",
        flyTo: { lat: 12.421, lng: 76.695, zoom: 13 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [76.62, 12.46],
            [76.74, 12.47],
            [76.78, 12.38],
            [76.65, 12.37],
            [76.60, 12.41],
            [76.62, 12.46]
          ]
        ]
      }
    },

    // 4. Maddur Taluk (Tender Coconut & Sericulture Capital)
    {
      type: "Feature",
      id: "maddur-coconut-sericulture",
      properties: {
        name: "Maddur Coconut & Sericulture Belt",
        taluk: "Maddur",
        district: "Mandya",
        state: "Karnataka",
        country: "India",
        cropTypeSummary: "Tender Coconut (Sihi Yele Neeru) & Mulberry Silk",
        primaryCrops: ["Tender Coconut", "Mulberry (V1 Hybrid Silk)", "Sugarcane", "Horse Gram"],
        category: "horticulture",
        areaHectares: 41200,
        ndviMean: 0.77,
        ndviColor: "#22c55e",
        soilType: "Red Gravelly Sandy Loam & Colluvial Valley Fills",
        soilPh: 6.6,
        irrigationSource: "Shimsha River & Maddur Branch Canals",
        irrigationCoverage: "78% Canal + Drip fertigation for coconut",
        croppingSeasons: "Year-round Coconut & Silk Cocoon harvest",
        annualRainfallMm: 685,
        sugarRecoveryRate: "9.8% (Tender Coconut APMC largest in Asia)",
        projectedYield: "12,000 nuts/ha/yr (Coconut) / 850 kg cocoon/ha",
        groundwaterDepthMeters: "15-25m",
        remoteSensingSource: "ISRO Bhuvan Horticulture / Sentinel-2",
        flyTo: { lat: 12.584, lng: 77.045, zoom: 12 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [76.98, 12.65],
            [77.12, 12.67],
            [77.16, 12.51],
            [77.05, 12.48],
            [76.96, 12.56],
            [76.98, 12.65]
          ]
        ]
      }
    },

    // 5. Malavalli & Shimsha Basin (Dryland Millets, Ragi & Silk)
    {
      type: "Feature",
      id: "malavalli-ragi",
      properties: {
        name: "Malavalli Ragi & Agro-Silvo Plain",
        taluk: "Malavalli",
        district: "Mandya",
        state: "Karnataka",
        country: "India",
        cropTypeSummary: "Finger Millet (Ragi), Mulberry & Cowpea",
        primaryCrops: ["Finger Millet (Ragi - GPU 28/ML 365)", "Cowpea (Alasande)", "Mulberry", "Sugarcane (tail-end)"],
        category: "millets_dryland",
        areaHectares: 39600,
        ndviMean: 0.68,
        ndviColor: "#84cc16",
        soilType: "Shallow Red Loamy Soils to Skeletal Lithic Soils",
        soilPh: 6.4,
        irrigationSource: "Shimsha River lift irrigation & Rainfed Watersheds",
        irrigationCoverage: "45% Irrigated (Tail-end of VC Canal)",
        croppingSeasons: "Kharif Rainfed (Jul-Nov) & Rabi Pulses",
        annualRainfallMm: 640,
        sugarRecoveryRate: "Tail-end canal command",
        projectedYield: "2.8 t/ha (Finger Millet) / 1.1 t/ha (Pulses)",
        groundwaterDepthMeters: "25-35m",
        remoteSensingSource: "ISRO FASAL / Sentinel-2",
        flyTo: { lat: 12.387, lng: 77.057, zoom: 12 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [76.96, 12.46],
            [77.14, 12.47],
            [77.18, 12.30],
            [77.02, 12.28],
            [76.94, 12.36],
            [76.96, 12.46]
          ]
        ]
      }
    },

    // 6. Nagamangala Plateau (Dryland Agro-Pastoral & Millets)
    {
      type: "Feature",
      id: "nagamangala-plateau",
      properties: {
        name: "Nagamangala Millet & Pulses Plateau",
        taluk: "Nagamangala",
        district: "Mandya",
        state: "Karnataka",
        country: "India",
        cropTypeSummary: "Rainfed Millets, Maize, Pulses & Sheep Rearing",
        primaryCrops: ["Finger Millet (Ragi)", "Hybrid Maize", "Red Gram (Togari)", "Field Bean (Avare)"],
        category: "millets_dryland",
        areaHectares: 51000,
        ndviMean: 0.62,
        ndviColor: "#84cc16",
        soilType: "Coarse Gravelly Red Soil & Granite Outcrops",
        soilPh: 6.2,
        irrigationSource: "Tanks (Kere), Check Dams & Deep Borewells",
        irrigationCoverage: "24% Tank/Groundwater fed (Semi-Arid Rainfed)",
        croppingSeasons: "Kharif Rainfed (Monsoon dependent)",
        annualRainfallMm: 610,
        sugarRecoveryRate: "Non-sugarcane zone",
        projectedYield: "2.2 t/ha (Ragi) / 4.2 t/ha (Maize)",
        groundwaterDepthMeters: "35-50m (Over-exploited dry zone)",
        remoteSensingSource: "Bhuvan Drought Telemetry / Landsat 9",
        flyTo: { lat: 12.821, lng: 76.758, zoom: 11 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [76.62, 12.98],
            [76.88, 12.95],
            [76.90, 12.70],
            [76.68, 12.68],
            [76.58, 12.82],
            [76.62, 12.98]
          ]
        ]
      }
    },

    // 7. Krishnarajpet (K.R. Pet) & Hemavati Catchment
    {
      type: "Feature",
      id: "kr-pet-hemavati",
      properties: {
        name: "K.R. Pet & Hemavati River Agro-Belt",
        taluk: "Krishnarajpet",
        district: "Mandya",
        state: "Karnataka",
        country: "India",
        cropTypeSummary: "Hemavati Canal Paddy, Sugarcane, Vegetables & Mango",
        primaryCrops: ["Paddy", "Sugarcane", "Mango Orchards", "Commercial Vegetables"],
        category: "sugar_paddy",
        areaHectares: 43800,
        ndviMean: 0.78,
        ndviColor: "#22c55e",
        soilType: "Medium Red Soil & Valley Clay Loam",
        soilPh: 6.7,
        irrigationSource: "Hemavati Left Bank Canal & Triveni Sangama",
        irrigationCoverage: "72% Canal & Lift Irrigation",
        croppingSeasons: "Dual Season Kharif-Rabi",
        annualRainfallMm: 670,
        sugarRecoveryRate: "10.1%",
        projectedYield: "98 t/ha (Sugarcane) / 5.6 t/ha (Paddy)",
        groundwaterDepthMeters: "14-22m",
        remoteSensingSource: "Sentinel-2 MSI / Bhuvan LULC",
        flyTo: { lat: 12.664, lng: 76.491, zoom: 12 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [76.38, 12.78],
            [76.58, 12.75],
            [76.60, 12.55],
            [76.44, 12.52],
            [76.36, 12.65],
            [76.38, 12.78]
          ]
        ]
      }
    },

    // 8. Krishna Raja Sagara (KRS) Dam & Reservoir (Hydrological Lifeline)
    {
      type: "Feature",
      id: "krs-reservoir-lifeline",
      properties: {
        name: "Krishna Raja Sagara (KRS) Catchment & Dam",
        taluk: "Srirangapatna / Mandya Border",
        district: "Mandya",
        state: "Karnataka",
        country: "India",
        cropTypeSummary: "Hydrological Headworks & Irrigation Storage",
        primaryCrops: ["Water Lifeline for 120,000+ ha Mandya Cropland"],
        category: "reservoir",
        areaHectares: 12900,
        ndviMean: 0.12,
        ndviColor: "#0284c7",
        soilType: "Submerged Lacustrine Silt & Granite Bedrock",
        soilPh: 7.3,
        irrigationSource: "Kaveri, Hemavati & Lakshmana Tirtha rivers",
        irrigationCoverage: "Feeds Visvesvaraya, Devaraja & Virija Canals",
        croppingSeasons: "Water release schedule: July 1 to Dec 31",
        annualRainfallMm: "Catchment rainfall: 2200mm (Kodagu / Western Ghats)",
        sugarRecoveryRate: "Powers entire Mandya sugar ecosystem",
        projectedYield: "Storage Capacity: 49.45 TMC ft (124.8 ft FSL)",
        groundwaterDepthMeters: "Reservoir Water Body",
        remoteSensingSource: "Sentinel-1 SAR / Sentinel-2 NDWI Water Index",
        flyTo: { lat: 12.428, lng: 76.572, zoom: 12 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [76.52, 12.48],
            [76.60, 12.44],
            [76.58, 12.40],
            [76.50, 12.42],
            [76.46, 12.46],
            [76.52, 12.48]
          ]
        ]
      }
    }
  ]
};

/**
 * Real-world Agronomic Telemetric Stations in Mandya District
 * Inspired by KSNDMC (Karnataka State Natural Disaster Monitoring Centre) and
 * UASB VC Farm (University of Agricultural Sciences Bangalore - ZARS Mandya)
 */
export const mandyaTelemetryStations = [
  {
    id: "KA-MDY-VCFARM",
    name: "ZARS VC Farm Agrometeorology",
    region: "Zonal Agricultural Research Station, Mandya",
    lat: 12.565,
    lng: 76.887,
    crop: "Sugarcane Co 86032 & Sona Masuri Foundation Seeds",
    soilMoisturePct: 36.8,
    canopyTempC: 26.4,
    humidityPct: 74,
    solarIrradianceWm2: 820,
    rainfall24hMm: 6.2,
    ndreIndex: 0.48,
    batteryPct: 98,
    status: "optimal",
    sourceOrg: "UAS Bangalore / KSNDMC Telemetry"
  },
  {
    id: "KA-MDY-PANDAVA",
    name: "Pandavapura Sugar Command Node #04",
    region: "Pandavapura Sahakari Sakkare Karkhane Belt",
    lat: 12.498,
    lng: 76.671,
    crop: "Ratoon Sugarcane & Wet Paddy",
    soilMoisturePct: 41.2,
    canopyTempC: 25.8,
    humidityPct: 78,
    solarIrradianceWm2: 790,
    rainfall24hMm: 11.4,
    ndreIndex: 0.51,
    batteryPct: 94,
    status: "optimal",
    sourceOrg: "Cane Development Directorate Karnataka"
  },
  {
    id: "KA-MDY-MADDUR",
    name: "Maddur Tender Coconut APMC Sensor",
    region: "Maddur Horticultural Corridor",
    lat: 12.583,
    lng: 77.042,
    crop: "Arsikere Tall x Chowghat Dwarf Hybrid Coconut",
    soilMoisturePct: 29.5,
    canopyTempC: 28.1,
    humidityPct: 62,
    solarIrradianceWm2: 890,
    rainfall24hMm: 2.0,
    ndreIndex: 0.42,
    batteryPct: 91,
    status: "optimal",
    sourceOrg: "Karnataka Horticultural Dept"
  },
  {
    id: "KA-MDY-SRIRANGA",
    name: "Srirangapatna Kaveri Island Station",
    region: "Paschimavahini Riverfront, Srirangapatna",
    lat: 12.418,
    lng: 76.691,
    crop: "Paddy (KRH-4) & Cavendish Banana",
    soilMoisturePct: 46.5,
    canopyTempC: 24.9,
    humidityPct: 82,
    solarIrradianceWm2: 750,
    rainfall24hMm: 14.8,
    ndreIndex: 0.53,
    batteryPct: 96,
    status: "optimal",
    sourceOrg: "Central Water Commission / KSNDMC"
  },
  {
    id: "KA-MDY-MALAVALLI",
    name: "Malavalli Tail-End Canal Probe",
    region: "Shimsha River Valley, Malavalli",
    lat: 12.389,
    lng: 77.054,
    crop: "Finger Millet (Ragi ML-365) & Cowpea",
    soilMoisturePct: 21.4,
    canopyTempC: 29.2,
    humidityPct: 53,
    solarIrradianceWm2: 910,
    rainfall24hMm: 0.0,
    ndreIndex: 0.35,
    batteryPct: 87,
    status: "warning",
    sourceOrg: "Watershed Development Dept Karnataka"
  },
  {
    id: "KA-MDY-NAGAMANGALA",
    name: "Nagamangala Dryland Watershed Node",
    region: "Bellur Cross Plateau, Nagamangala",
    lat: 12.820,
    lng: 76.756,
    crop: "Dryland Ragi & Fodder Maize",
    soilMoisturePct: 17.1,
    canopyTempC: 31.0,
    humidityPct: 42,
    solarIrradianceWm2: 960,
    rainfall24hMm: 0.0,
    ndreIndex: 0.31,
    batteryPct: 83,
    status: "stress",
    sourceOrg: "KSNDMC Drought Telemetry"
  },
  {
    id: "KA-MDY-KRPET",
    name: "K.R. Pet Hemavati Confluence Node",
    region: "Krishnarajpet Valley, Mandya",
    lat: 12.662,
    lng: 76.495,
    crop: "Canal Irrigated Paddy & Mango Orchards",
    soilMoisturePct: 34.0,
    canopyTempC: 27.0,
    humidityPct: 69,
    solarIrradianceWm2: 830,
    rainfall24hMm: 4.5,
    ndreIndex: 0.44,
    batteryPct: 95,
    status: "optimal",
    sourceOrg: "Cauvery Neeravari Nigam Limited (CNNL)"
  },
  {
    id: "KA-MDY-KRS",
    name: "KRS Dam Headworks Hydrometric Station",
    region: "Krishna Raja Sagara Dam Crest, Mandya",
    lat: 12.427,
    lng: 76.574,
    crop: "Hydrological Reservoir (124.8 ft Live Storage)",
    soilMoisturePct: 98.0,
    canopyTempC: 23.5,
    humidityPct: 88,
    solarIrradianceWm2: 710,
    rainfall24hMm: 22.0,
    ndreIndex: 0.15,
    batteryPct: 99,
    status: "optimal",
    sourceOrg: "Water Resources Dept / CNNL"
  }
];
