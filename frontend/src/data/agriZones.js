export const agriZonesGeoJSON = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: "us-corn-belt",
      properties: {
        name: "US Corn & Soybean Belt",
        region: "Midwest, United States",
        country: "USA",
        category: "grains",
        primaryCrops: ["Field Corn", "Soybeans", "Winter Wheat"],
        cropTypeSummary: "Maize & Legumes",
        areaHectares: 45000000,
        ndviMean: 0.79,
        ndviColor: "#22c55e",
        soilType: "Mollisols (Deep Prairie Chernozem-like)",
        soilPh: 6.5,
        irrigationType: "Rainfed & Center-Pivot (38%)",
        growingSeason: "April – October",
        projectedYield: "11.2 t/ha (Corn) / 3.4 t/ha (Soy)",
        moistureStatus: "Adequate (+4% vs 10yr avg)",
        temperatureCanopy: "22.4°C",
        riskAlert: "Low - High Canopy Density",
        satelliteMission: "Sentinel-2 MSI / Landsat 9 OLI-2",
        flyTo: { lat: 41.5, lng: -93.5, zoom: 6 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-98.5, 41.0],
            [-96.8, 43.8],
            [-93.5, 45.2],
            [-88.5, 44.5],
            [-84.5, 41.8],
            [-84.2, 39.2],
            [-89.5, 38.5],
            [-94.8, 39.0],
            [-98.5, 41.0]
          ]
        ]
      }
    },
    {
      type: "Feature",
      id: "california-central-valley",
      properties: {
        name: "Central Valley Agro-Corridor",
        region: "California, United States",
        country: "USA",
        category: "specialty",
        primaryCrops: ["Almonds", "Pistachios", "Wine Grapes", "Processing Tomatoes", "Citrus"],
        cropTypeSummary: "Orchard & High-Value Horticultural",
        areaHectares: 5200000,
        ndviMean: 0.64,
        ndviColor: "#84cc16",
        soilType: "Entisols & Vertisols (Alluvial Floodplain)",
        soilPh: 7.2,
        irrigationType: "Micro-Drip & Canal Aqueduct (92%)",
        growingSeason: "Year-round (Multi-crop microclimates)",
        projectedYield: "High Cash Output / Micro-monitored",
        moistureStatus: "Groundwater Depletion Monitored (-11%)",
        temperatureCanopy: "28.1°C",
        riskAlert: "Moderate - Evapotranspiration Deficit",
        satelliteMission: "ECOSTRESS / Sentinel-2 Thermal",
        flyTo: { lat: 36.8, lng: -119.8, zoom: 7 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-122.2, 40.2],
            [-121.5, 39.5],
            [-120.2, 37.8],
            [-118.8, 35.2],
            [-119.5, 35.0],
            [-120.8, 36.4],
            [-121.8, 38.2],
            [-122.5, 39.8],
            [-122.2, 40.2]
          ]
        ]
      }
    },
    {
      type: "Feature",
      id: "mato-grosso-cerrado",
      properties: {
        name: "Mato Grosso Cerrado Agricultural Belt",
        region: "Center-West, Brazil",
        country: "Brazil",
        category: "oilseeds",
        primaryCrops: ["Soybean (Safrinha)", "Maize", "Upland Cotton"],
        cropTypeSummary: "Intensive Double-Cropping",
        areaHectares: 32000000,
        ndviMean: 0.83,
        ndviColor: "#15803d",
        soilType: "Oxisols / Red-Yellow Latosols (Deep Acidic, Limed)",
        soilPh: 5.8,
        irrigationType: "Sub-humid Tropical Double Crop (18% Irrigated)",
        growingSeason: "October – June (Dual Harvest)",
        projectedYield: "3.9 t/ha (Soy) / 6.8 t/ha (Safrinha Maize)",
        moistureStatus: "Optimal (+7% Monsoonal Soil Storage)",
        temperatureCanopy: "27.8°C",
        riskAlert: "Low - High Biomass Accumulation",
        satelliteMission: "CBERS-4 / Sentinel-2 / MODIS",
        flyTo: { lat: -12.8, lng: -55.8, zoom: 6 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-59.2, -10.5],
            [-54.0, -10.8],
            [-51.8, -13.5],
            [-52.5, -16.8],
            [-56.5, -16.2],
            [-58.8, -14.2],
            [-59.2, -10.5]
          ]
        ]
      }
    },
    {
      type: "Feature",
      id: "argentine-pampas",
      properties: {
        name: "Humid Pampas Granary",
        region: "Buenos Aires / Santa Fe / Córdoba, Argentina",
        country: "Argentina",
        category: "grains",
        primaryCrops: ["Soybean", "Bread Wheat", "Maize", "Sunflower"],
        cropTypeSummary: "Temperate Grain & Oilseed Plain",
        areaHectares: 48000000,
        ndviMean: 0.73,
        ndviColor: "#16a34a",
        soilType: "Chernozemic Mollisols (Silty Loess)",
        soilPh: 6.4,
        irrigationType: "Predominantly Rainfed (91%)",
        growingSeason: "September – May",
        projectedYield: "3.2 t/ha (Soy) / 4.1 t/ha (Wheat)",
        moistureStatus: "Stable (+1%)",
        temperatureCanopy: "20.5°C",
        riskAlert: "Normal - Seasonal Maturation",
        satelliteMission: "Landsat 8/9 / Sentinel-2 MSI",
        flyTo: { lat: -34.5, lng: -61.5, zoom: 6 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-64.5, -31.5],
            [-60.5, -31.2],
            [-58.5, -34.0],
            [-57.5, -37.5],
            [-61.5, -38.8],
            [-64.8, -36.0],
            [-64.5, -31.5]
          ]
        ]
      }
    },
    {
      type: "Feature",
      id: "ukrainian-chernozem",
      properties: {
        name: "Ukrainian Chernozem Belt",
        region: "Central & Southern Steppe, Ukraine",
        country: "Ukraine",
        category: "grains",
        primaryCrops: ["Winter Wheat", "Sunflower Seed", "Barley", "Corn"],
        cropTypeSummary: "High-Fertility Black Soil Steppe",
        areaHectares: 38000000,
        ndviMean: 0.71,
        ndviColor: "#16a34a",
        soilType: "Typical Deep Chernozem (8–12% Humus Content)",
        soilPh: 6.8,
        irrigationType: "Dryland Rainfed & Dnieper Canals (12%)",
        growingSeason: "April – September",
        projectedYield: "4.8 t/ha (Wheat) / 2.3 t/ha (Sunflower)",
        moistureStatus: "Slight Deficit (-5% continental drought)",
        temperatureCanopy: "18.6°C",
        riskAlert: "Moderate - Soil Moisture Watch",
        satelliteMission: "Sentinel-2 L2A / PlanetScope",
        flyTo: { lat: 48.5, lng: 32.5, zoom: 6 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [27.5, 49.5],
            [34.5, 51.0],
            [38.5, 49.5],
            [37.2, 47.0],
            [32.8, 46.5],
            [29.0, 47.8],
            [27.5, 49.5]
          ]
        ]
      }
    },
    {
      type: "Feature",
      id: "indo-gangetic-plain",
      properties: {
        name: "Indo-Gangetic Alluvial Basin",
        region: "Punjab, Haryana, Uttar Pradesh, India / Pakistan",
        country: "India / Pakistan",
        category: "grains",
        primaryCrops: ["Basmati Rice", "Rabi Wheat", "Sugarcane", "Mustard"],
        cropTypeSummary: "Intensive Smallholder Paddy-Wheat Rotation",
        areaHectares: 41000000,
        ndviMean: 0.69,
        ndviColor: "#84cc16",
        soilType: "Recent Alluvium (Khadar & Bhangar Silts)",
        soilPh: 7.4,
        irrigationType: "Extensive Canal & Groundwater Tubewell (85%)",
        growingSeason: "Kharif (Monsoon: Jun-Nov) & Rabi (Nov-Apr)",
        projectedYield: "4.5 t/ha (Rice) / 4.9 t/ha (Wheat)",
        moistureStatus: "High Aquifer Exploitation (+6% Monsoon runoff)",
        temperatureCanopy: "26.9°C",
        riskAlert: "Watch - Stubble Burning & Groundwater Depletion",
        satelliteMission: "RISAT-1A SAR / Sentinel-1 C-Band",
        flyTo: { lat: 28.5, lng: 77.8, zoom: 6 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [72.5, 31.8],
            [76.8, 31.2],
            [82.5, 27.5],
            [87.5, 25.8],
            [88.2, 24.2],
            [83.5, 24.8],
            [77.0, 27.5],
            [72.0, 29.8],
            [72.5, 31.8]
          ]
        ]
      }
    },
    {
      type: "Feature",
      id: "sanjiang-plain",
      properties: {
        name: "Northeast China Plain (Heilongjiang)",
        region: "Northeast China",
        country: "China",
        category: "grains",
        primaryCrops: ["Japonica Cold-Tolerant Rice", "Maize", "Spring Wheat", "Soybean"],
        cropTypeSummary: "Mechanized Mega-Paddies & Cold Steppe Grain",
        areaHectares: 35000000,
        ndviMean: 0.76,
        ndviColor: "#22c55e",
        soilType: "Phaeozem & Black Calcium Soil",
        soilPh: 6.2,
        irrigationType: "River Diversion & Controlled Flood (68%)",
        growingSeason: "May – October (Single High-Yield Cycle)",
        projectedYield: "8.6 t/ha (Japonica Rice) / 9.1 t/ha (Maize)",
        moistureStatus: "Sufficient (+3%)",
        temperatureCanopy: "19.2°C",
        riskAlert: "Low - High Thermal Unit Accumulation",
        satelliteMission: "Gaofen-1 / Sentinel-2 MSI",
        flyTo: { lat: 46.8, lng: 130.5, zoom: 6 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [124.5, 48.5],
            [131.5, 48.0],
            [134.5, 47.0],
            [132.8, 44.5],
            [127.0, 44.0],
            [123.8, 46.2],
            [124.5, 48.5]
          ]
        ]
      }
    },
    {
      type: "Feature",
      id: "po-river-valley",
      properties: {
        name: "Po Valley Agronomic Basin",
        region: "Lombardy / Emilia-Romagna / Veneto, Italy",
        country: "Italy",
        category: "specialty",
        primaryCrops: ["Arborio/Carnaroli Rice", "Silage Maize", "Parmigiano Forage", "Vineyards"],
        cropTypeSummary: "Precision Alpine Alluvium Agriculture",
        areaHectares: 4700000,
        ndviMean: 0.74,
        ndviColor: "#22c55e",
        soilType: "Fluvisols & Inceptisols (Alpine Glacial Silt)",
        soilPh: 7.0,
        irrigationType: "Cavour Historical Canal & Sub-irrigation (76%)",
        growingSeason: "March – October",
        projectedYield: "6.8 t/ha (Specialty Rice) / 12.0 t/ha (Maize)",
        moistureStatus: "Controlled (+2%)",
        temperatureCanopy: "21.0°C",
        riskAlert: "Normal - Stable Alpine Snowpack Flow",
        satelliteMission: "PRISMA Hyperspectral / Sentinel-2",
        flyTo: { lat: 45.2, lng: 10.5, zoom: 7 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [7.8, 45.3],
            [10.2, 45.6],
            [12.5, 45.5],
            [12.5, 44.6],
            [10.0, 44.8],
            [8.2, 44.9],
            [7.8, 45.3]
          ]
        ]
      }
    },
    {
      type: "Feature",
      id: "nile-river-delta",
      properties: {
        name: "Nile Delta & Valley Oasis",
        region: "Lower Nile, Egypt",
        country: "Egypt",
        category: "specialty",
        primaryCrops: ["Long-Staple Giza Cotton", "Delta Rice", "Clover (Berseem)", "Citrus"],
        cropTypeSummary: "Hyper-Dense Perennial Irrigated Oasis",
        areaHectares: 3200000,
        ndviMean: 0.62,
        ndviColor: "#84cc16",
        soilType: "Vertic Alluvial Smectite Clay",
        soilPh: 8.1,
        irrigationType: "100% Perennial Gravity & Pumped Canals",
        growingSeason: "Year-round (Tri-annual crop rotation)",
        projectedYield: "4.2 t/ha (Cotton) / 9.5 t/ha (Delta Rice)",
        moistureStatus: "Regulated via Lake Nasser discharge",
        temperatureCanopy: "29.4°C",
        riskAlert: "Elevated - Salinity & High Evaporation",
        satelliteMission: "PlanetScope SkySat / Sentinel-2",
        flyTo: { lat: 30.8, lng: 31.2, zoom: 8 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [29.8, 31.2],
            [31.8, 31.5],
            [32.3, 30.9],
            [31.5, 30.1],
            [30.8, 30.0],
            [29.8, 30.8],
            [29.8, 31.2]
          ]
        ]
      }
    },
    {
      type: "Feature",
      id: "murray-darling-basin",
      properties: {
        name: "Murray-Darling Agrarian Basin",
        region: "New South Wales / Victoria, Australia",
        country: "Australia",
        category: "grains",
        primaryCrops: ["Hard Winter Wheat", "Barley", "Canola", "Wine Grapes", "Irrigated Cotton"],
        cropTypeSummary: "Extensive Semi-Arid Grain & Managed Catchment",
        areaHectares: 42000000,
        ndviMean: 0.58,
        ndviColor: "#eab308",
        soilType: "Vertosols (Self-Mulching Cracking Clays)",
        soilPh: 7.5,
        irrigationType: "Basin Water Rights Allotted Irrigation (23%)",
        growingSeason: "May – November (Winter-Spring)",
        projectedYield: "2.8 t/ha (Wheat) / 2.1 t/ha (Canola)",
        moistureStatus: "Deficit monitored (-9% Southern Oscillation)",
        temperatureCanopy: "24.2°C",
        riskAlert: "Moderate - Soil Moisture Depletion",
        satelliteMission: "Landsat-9 / Sentinel-2 / Himawari-8",
        flyTo: { lat: -34.0, lng: 144.5, zoom: 6 }
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [141.0, -32.0],
            [146.5, -30.0],
            [149.8, -32.5],
            [148.5, -36.5],
            [144.0, -36.2],
            [140.5, -34.5],
            [141.0, -32.0]
          ]
        ]
      }
    }
  ]
};
