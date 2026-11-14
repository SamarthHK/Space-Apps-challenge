/**
 * Storage Service — Client-side Persistence Repository
 * Manages localStorage for Farmer Profile, Plots, Soil Health Cards, and Planting Plans
 */

const STORAGE_KEYS = {
  FARMER_PROFILE: "agri_intel_farmer_profile",
  PLOTS: "agri_intel_plots",
  PLANTING_PLANS: "agri_intel_planting_plans",
  CUSTOM_SETTINGS: "agri_intel_settings"
};

// Default seed data for a Karnataka farmer (Tumakuru & Mandya pilot)
const INITIAL_FARMER_PROFILE = {
  name: "Shivalingaiah Gowda",
  kannadaName: "ಶಿವಲಿಂಗಯ್ಯ ಗೌಡ",
  phone: "+91 98450 12345",
  village: "Hirehalli (ಹಿರೇಹಳ್ಳಿ)",
  taluk: "Tumakuru",
  district: "Tumakuru",
  state: "Karnataka",
  soilHealthCardNo: "SHC-KA-TUM-2026-88412",
  farmerCategory: "Small & Marginal Farmer (ಸಣ್ಣ ರೈತ)",
  preferredLanguage: "en", // 'en' | 'kn'
  riskTolerance: "balanced", // 'conservative' | 'balanced' | 'progressive'
  primaryObjective: "profit_maximization" // 'profit_maximization' | 'food_security' | 'low_risk'
};

const INITIAL_PLOTS = [
  {
    id: "plot-tum-01",
    name: "Hirehalli North Dryland Plot (ಉತ್ತರ ಜಮೀನು)",
    district: "Tumakuru",
    taluk: "Tumakuru",
    village: "Hirehalli",
    surveyNumber: "Sy. No. 42/3",
    areaAcre: 3.25,
    areaGuntas: 130,
    areaHectares: 1.31,
    coordinates: [13.2974, 77.1262],
    // GeoJSON Polygon for the parcel
    boundary: {
      type: "Polygon",
      coordinates: [
        [
          [77.1245, 13.2985],
          [77.1280, 13.2982],
          [77.1278, 13.2958],
          [77.1248, 13.2961],
          [77.1245, 13.2985]
        ]
      ]
    },
    irrigationType: "rainfed", // rainfed, borewell, canal, drip, sprinkler
    waterAvailability: "medium_seasonal", // high_perennial, medium_seasonal, low_critical
    previousCrops: ["Groundnut (TMV-2) - Kharif 2025", "Horse Gram (Huruli) - Rabi catch crop"],
    soilRecord: {
      hasSoilTest: true,
      cardNo: "SHC-KA-TUM-2026-88412",
      testDate: "2026-05-18",
      labName: "ICAR-KVK Hirehalli Soil Testing Lab",
      texture: "red_sandy_loam", // red_sandy_loam, black_soil, clay_loam, alluvial, laterite
      textureDisplay: "Red Sandy Loam (ಕೆಂಪು ಮರಳು ಮಣ್ಣು)",
      ph: 6.6,
      phStatus: "Slightly Acidic to Neutral (Optimal)",
      electricalConductivity: 0.32, // dS/m
      ecStatus: "Normal (Non-saline)",
      organicCarbonPct: 0.52,
      ocStatus: "Medium (0.50 - 0.75%)",
      nitrogenKgHa: 215,
      nitrogenStatus: "Low (< 280 kg/ha)",
      phosphorusKgHa: 22.4,
      phosphorusStatus: "Medium (10 - 25 kg/ha)",
      potassiumKgHa: 275,
      potassiumStatus: "High (> 280 kg/ha is high, 275 is High)",
      soilDepth: "medium", // shallow (<30cm), medium (30-60cm), deep (>60cm)
      drainage: "well_drained",
      waterHoldingCapacity: "Moderate (35-42%)"
    },
    waterRecord: {
      source: "Seasonal Rain + 1 Community Borewell",
      borewellReliability: "Seasonal (3 months summer drying)",
      borewellDepthFt: 450,
      groundwaterYieldInches: 1.5,
      irrigationCostPerHour: 120, // Electricity / generator diesel share
      waterQuality: "Good (Potable & low sodium hazard)"
    },
    satelliteSummary: {
      latestNdvi: 0.74,
      canopyCondition: "High Biomass / Active Tillering",
      vegetationAnomaly: "+8% vs 3-yr baseline",
      cloudCoverLatest: 2
    }
  },

  {
    id: "plot-tum-02",
    name: "Kallambella Valley Field (ಕಲ್ಲಂಬೆಳ್ಳ ಹೊಲ)",
    district: "Tumakuru",
    taluk: "Sira",
    village: "Kallambella",
    surveyNumber: "Sy. No. 118/1B",
    areaAcre: 2.10,
    areaGuntas: 84,
    areaHectares: 0.85,
    coordinates: [13.6215, 76.9210],
    boundary: {
      type: "Polygon",
      coordinates: [
        [
          [76.9192, 13.6225],
          [76.9230, 13.6220],
          [76.9226, 13.6198],
          [76.9195, 13.6202],
          [76.9192, 13.6225]
        ]
      ]
    },
    irrigationType: "borewell",
    waterAvailability: "high_perennial",
    previousCrops: ["Finger Millet (Ragi GPU-28) - Kharif 2025", "Chickpea (Bengal Gram) - Rabi 2025"],
    soilRecord: {
      hasSoilTest: true,
      cardNo: "SHC-KA-SRA-2026-44102",
      testDate: "2026-06-04",
      labName: "District Soil Health Center, Tumakuru",
      texture: "clay_loam",
      textureDisplay: "Medium Black Clay Loam (ಮಧ್ಯಮ ಕಪ್ಪು ಮಣ್ಣು)",
      ph: 7.6,
      phStatus: "Slightly Alkaline (Acceptable)",
      electricalConductivity: 0.48,
      ecStatus: "Normal",
      organicCarbonPct: 0.65,
      ocStatus: "Medium",
      nitrogenKgHa: 240,
      nitrogenStatus: "Low to Medium",
      phosphorusKgHa: 28.5,
      phosphorusStatus: "High (> 25 kg/ha)",
      potassiumKgHa: 310,
      potassiumStatus: "High",
      soilDepth: "deep",
      drainage: "moderate",
      waterHoldingCapacity: "High (50-60%)"
    },
    waterRecord: {
      source: "Dedicated Borewell with Solar Pump",
      borewellReliability: "High Perennial (Year-round 2.5 inches)",
      borewellDepthFt: 380,
      groundwaterYieldInches: 2.5,
      irrigationCostPerHour: 40, // Solar subsidized
      waterQuality: "Neutral pH, Total Dissolved Solids 420 ppm"
    },
    satelliteSummary: {
      latestNdvi: 0.82,
      canopyCondition: "Peak Canopy Density",
      vegetationAnomaly: "+12% vs baseline",
      cloudCoverLatest: 5
    }
  },

  {
    id: "plot-man-03",
    name: "Pandavapura Sugar Strip (ಪಾಂಡವಪುರ ಕಬ್ಬಿನ ಗದ್ದೆ)",
    district: "Mandya",
    taluk: "Pandavapura",
    village: "Chikka Byadarahalli",
    surveyNumber: "Sy. No. 84/2",
    areaAcre: 1.80,
    areaGuntas: 72,
    areaHectares: 0.73,
    coordinates: [12.5028, 76.7165],
    boundary: {
      type: "Polygon",
      coordinates: [
        [
          [76.7145, 12.5040],
          [76.7182, 12.5036],
          [76.7178, 12.5015],
          [76.7149, 12.5018],
          [76.7145, 12.5040]
        ]
      ]
    },
    irrigationType: "canal",
    waterAvailability: "high_perennial",
    previousCrops: ["Sugarcane (Co 86032)", "Sona Masuri Paddy"],
    soilRecord: {
      hasSoilTest: false, // Testing unverified scenario
      cardNo: "",
      testDate: "",
      labName: "",
      texture: "alluvial",
      textureDisplay: "Alluvial Clay (ಕಾವೇರಿ ಮೆಕ್ಕಲು ಮಣ್ಣು - Estimated)",
      ph: 7.0,
      phStatus: "Neutral (Estimated)",
      electricalConductivity: 0.38,
      ecStatus: "Normal",
      organicCarbonPct: 0.72,
      ocStatus: "Good",
      nitrogenKgHa: 260,
      nitrogenStatus: "Medium",
      phosphorusKgHa: 30.0,
      phosphorusStatus: "High",
      potassiumKgHa: 290,
      potassiumStatus: "High",
      soilDepth: "deep",
      drainage: "slow_draining",
      waterHoldingCapacity: "Very High (>60%)"
    },
    waterRecord: {
      source: "Visvesvaraya Canal (VC Canal) Command",
      borewellReliability: "Canal rotational schedule (10 days on / 10 days off)",
      borewellDepthFt: 0,
      groundwaterYieldInches: 0,
      irrigationCostPerHour: 25, // Water cess per acre per year
      waterQuality: "Excellent Kaveri river surface runoff"
    },
    satelliteSummary: {
      latestNdvi: 0.88,
      canopyCondition: "Peak Sugar Canopy",
      vegetationAnomaly: "+15% vs baseline",
      cloudCoverLatest: 2
    }
  }
];

const INITIAL_PLANS = [
  {
    id: "plan-001",
    plotId: "plot-tum-01",
    plotName: "Hirehalli North Dryland Plot",
    cropId: "ragi-gpu28",
    cropName: "Finger Millet (Ragi - GPU 28)",
    kannadaName: "ರಾಗಿ (ಜಿಪಿಯು-೨೮)",
    cultivatedAcre: 3.25,
    sowingWindow: "July 10, 2026",
    harvestWindow: "November 15, 2026",
    budgetCostTotal: 62400, // ₹19,200 * 3.25
    expectedGrossRevenue: 198031, // 14 qtl/ac * 3.25 * ₹4,350
    expectedNetReturn: 135631, // ₹41,732/ac profit
    pessimisticNetReturn: 42900,
    optimisticNetReturn: 249600,
    waterRequirementMm: 450,
    irrigationStrategy: "Rainfed with 1 protective irrigation during flowering via neighbor borewell",
    keyRisks: ["Blast leaf disease if late August rains are continuous", "Spikelet sterility during drought spell"],
    status: "Active Planned",
    createdAt: "2026-06-15"
  },
  {
    id: "plan-002",
    plotId: "plot-tum-02",
    plotName: "Kallambella Valley Field",
    cropId: "pigeonpea-brg2",
    cropName: "Pigeon Pea (Red Gram / Tur - BRG 2)",
    kannadaName: "ತೊಗರಿ (ಬಿಆರ್‌ಜಿ-೨)",
    cultivatedAcre: 2.10,
    sowingWindow: "June 28, 2026",
    harvestWindow: "January 10, 2027",
    budgetCostTotal: 42000,
    expectedGrossRevenue: 141120, // 8 qtl/ac * 2.1 * ₹8,400
    expectedNetReturn: 99120,
    pessimisticNetReturn: 29400,
    optimisticNetReturn: 204960,
    waterRequirementMm: 600,
    irrigationStrategy: "Solar drip irrigation every 8 days during pod development stage",
    keyRisks: ["Helicoverpa pod borer infestation during November flowering"],
    status: "Active Planned",
    createdAt: "2026-06-20"
  }
];

export const storageService = {
  // Farmer Profile
  getProfile() {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.FARMER_PROFILE);
      return data ? JSON.parse(data) : INITIAL_FARMER_PROFILE;
    } catch {
      return INITIAL_FARMER_PROFILE;
    }
  },

  saveProfile(profile) {
    try {
      localStorage.setItem(STORAGE_KEYS.FARMER_PROFILE, JSON.stringify(profile));
      return true;
    } catch (e) {
      console.error("Failed to save profile", e);
      return false;
    }
  },

  // Plots
  getPlots() {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.PLOTS);
      if (data) {
        const parsed = JSON.parse(data);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
      // Seed if empty
      this.savePlots(INITIAL_PLOTS);
      return INITIAL_PLOTS;
    } catch {
      return INITIAL_PLOTS;
    }
  },

  savePlots(plots) {
    try {
      localStorage.setItem(STORAGE_KEYS.PLOTS, JSON.stringify(plots));
      return true;
    } catch (e) {
      console.error("Failed to save plots", e);
      return false;
    }
  },

  getPlotById(id) {
    const plots = this.getPlots();
    return plots.find(p => p.id === id) || plots[0];
  },

  addPlot(newPlot) {
    const plots = this.getPlots();
    plots.push(newPlot);
    this.savePlots(plots);
    return newPlot;
  },

  updatePlot(updatedPlot) {
    const plots = this.getPlots();
    const index = plots.findIndex(p => p.id === updatedPlot.id);
    if (index !== -1) {
      plots[index] = updatedPlot;
      this.savePlots(plots);
      return true;
    }
    return false;
  },

  deletePlot(plotId) {
    const plots = this.getPlots();
    const filtered = plots.filter(p => p.id !== plotId);
    this.savePlots(filtered);
    return true;
  },

  // Planting Plans
  getPlans() {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.PLANTING_PLANS);
      if (data) {
        const parsed = JSON.parse(data);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
      this.savePlans(INITIAL_PLANS);
      return INITIAL_PLANS;
    } catch {
      return INITIAL_PLANS;
    }
  },

  savePlans(plans) {
    try {
      localStorage.setItem(STORAGE_KEYS.PLANTING_PLANS, JSON.stringify(plans));
      return true;
    } catch (e) {
      console.error("Failed to save plans", e);
      return false;
    }
  },

  addPlan(newPlan) {
    const plans = this.getPlans();
    plans.unshift(newPlan);
    this.savePlans(plans);
    return newPlan;
  },

  deletePlan(planId) {
    const plans = this.getPlans();
    const filtered = plans.filter(p => p.id !== planId);
    this.savePlans(filtered);
    return true;
  },

  // Reset to factory defaults
  resetToDefaults() {
    localStorage.setItem(STORAGE_KEYS.FARMER_PROFILE, JSON.stringify(INITIAL_FARMER_PROFILE));
    localStorage.setItem(STORAGE_KEYS.PLOTS, JSON.stringify(INITIAL_PLOTS));
    localStorage.setItem(STORAGE_KEYS.PLANTING_PLANS, JSON.stringify(INITIAL_PLANS));
    return true;
  }
};
