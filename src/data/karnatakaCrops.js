/**
 * Karnataka Crop Database — Pilot Validation Dataset
 * Region Focus: Tumakuru & Mandya Agro-Ecological Zones (Southern Dry Zone & Southern Transition Zone)
 * Sources: UAS Bangalore, ICAR-KVK Tumakuru, Karnataka State Department of Agriculture (KSDA)
 */

export const karnatakaCrops = [
  {
    id: "ragi-gpu28",
    name: "Finger Millet (Ragi)",
    kannadaName: "ರಾಗಿ",
    scientificName: "Eleusine coracana",
    popularVarieties: ["GPU-28", "ML-365", "MR-1", "KMR-301"],
    season: "kharif", // kharif, rabi, summer
    cropDurationDays: 115,
    sowingWindow: "July 1st to August 15th",
    harvestWindow: "November 1st to December 15th",
    category: "millets",
    
    // Agronomic Suitability Criteria (Stage A Filtering)
    soilSuitability: {
      suitableTextures: ["red_sandy_loam", "red_loam", "clay_loam", "laterite"],
      phMin: 5.5,
      phMax: 7.8,
      optimalPh: 6.5,
      soilDepthRequired: "medium", // shallow, medium, deep
      drainageRequirements: ["moderate", "good", "well_drained"],
      droughtTolerance: "very_high",
      waterloggingTolerance: "low"
    },
    waterRequirements: {
      totalMm: 450, // 400 - 500 mm
      minRainfallMm: 380,
      sensitivity: "low",
      irrigationNeeds: "Can be grown entirely rainfed; 1-2 protective irrigations during tillering & flowering boost yield by 35%."
    },
    climateRequirements: {
      minTempC: 18,
      maxTempC: 36,
      optimalTempC: 27
    },

    // Yield Metrics (Quintals per Acre)
    yieldPerAcre: {
      pessimistic: 9,   // Drought / rain deficit
      expected: 14,     // Average rainfed with good management
      optimistic: 20    // Protective irrigation + balanced NPK
    },

    // Cost of Cultivation per Acre (₹ INR) - Detailed Breakdown
    cultivationCostPerAcre: {
      landPreparation: 2800,  // Tractor ploughing, harrowing, leveling
      seeds: 600,             // 4 kg/acre certified seed + seed treatment
      farmyardManure: 3500,   // 3 tonnes FYM / organic compost
      fertilizers: 2200,      // Urea, DAP, MOP, Zinc sulphate
      sowingAndTransplanting: 2400, // Line sowing / transplanting labour
      weedingAndIntercultivation: 2200, // Cycle weeding / bullock pass
      plantProtection: 800,   // Bio-fungicide / blast control
      harvestingAndThreshing: 3800, // Manual harvesting & machine threshing
      postHarvestTransport: 900, // Bagging & transport to APMC mandi
      total: 19200
    },

    // Farm-Gate / APMC Price Expectations (₹ per Quintal)
    pricePerQuintal: {
      msp: 4290,        // Karnataka Govt MSP procurement support
      pessimistic: 3600, // Harvest glut local trader price
      expected: 4350,   // Mandi modal price
      optimistic: 4800  // High quality grain / offseason market
    },

    // Main Agricultural Risks & Mitigation
    pestsAndDiseases: [
      {
        name: "Ragi Blast (Pyricularia grisea)",
        riskLevel: "Moderate",
        symptoms: "Spindle-shaped lesions on leaves; neck/finger blast reduces grain filling.",
        management: "Seed treatment with Trichoderma viride or Carbendazim; avoid excess urea."
      },
      {
        name: "Stem Borer & Earhead Caterpillars",
        riskLevel: "Low",
        symptoms: "Dead hearts during vegetative stage; chewed grains on earhead.",
        management: "Pheromone traps; spray Neem oil 3000 ppm during boot leaf stage."
      }
    ],

    localGuidance: {
      source: "UAS Bangalore / KVK Hirehalli, Tumakuru",
      keyAdvantage: "Extremely resilient crop for Tumakuru dryland belts; high nutritional demand, guaranteed MSP procurement via KSFA.",
      recommendationSummary: "Top recommendation for red sandy soils with erratic Kharif rainfall."
    }
  },

  {
    id: "groundnut-tmv2",
    name: "Groundnut (Peanut)",
    kannadaName: "ಕಡಲೆಕಾಯಿ",
    scientificName: "Arachis hypogaea",
    popularVarieties: ["TMV-2", "GPBD-4", "KCG-6", "ICGV 91114"],
    season: "kharif",
    cropDurationDays: 105,
    sowingWindow: "June 25th to July 25th",
    harvestWindow: "October 15th to November 20th",
    category: "oilseeds",

    soilSuitability: {
      suitableTextures: ["red_sandy_loam", "sandy_loam", "loamy_sand"],
      phMin: 6.0,
      phMax: 7.8,
      optimalPh: 6.5,
      soilDepthRequired: "medium",
      drainageRequirements: ["good", "well_drained"],
      droughtTolerance: "high",
      waterloggingTolerance: "very_low" // Heavy clay impedes pegging
    },
    waterRequirements: {
      totalMm: 500,
      minRainfallMm: 420,
      sensitivity: "moderate",
      irrigationNeeds: "Critical moisture required during pegging and pod development stages (50-75 days after sowing)."
    },
    climateRequirements: {
      minTempC: 20,
      maxTempC: 35,
      optimalTempC: 28
    },

    yieldPerAcre: {
      pessimistic: 6,
      expected: 10,
      optimistic: 15
    },

    cultivationCostPerAcre: {
      landPreparation: 3200,
      seeds: 5400,            // Pod seed cost is significant (40-45 kg pods)
      farmyardManure: 3000,
      fertilizers: 2600,      // Gypsum (200kg/acre at flowering is crucial for pod fill)
      sowingAndTransplanting: 2000,
      weedingAndIntercultivation: 2500,
      plantProtection: 1400,
      harvestingAndThreshing: 4500, // Manual digging, plucking, drying
      postHarvestTransport: 1000,
      total: 25600
    },

    pricePerQuintal: {
      msp: 6783,
      pessimistic: 5600,
      expected: 6850,
      optimistic: 7600
    },

    pestsAndDiseases: [
      {
        name: "Tikka Leaf Spot & Rust",
        riskLevel: "High",
        symptoms: "Circular dark brown spots with chlorotic halos causing premature defoliation.",
        management: "Spray Mancozeb @ 2 g/L or Hexaconazole @ 1 ml/L at first appearance."
      },
      {
        name: "White Grub (Holotrichia serrata)",
        riskLevel: "Moderate",
        symptoms: "Roots chewed off causing patchy wilting of plants.",
        management: "Deep summer ploughing; soil application of Metarhizium anisopliae."
      }
    ],

    localGuidance: {
      source: "ICAR-KVK Tumakuru & UAS Dharwad",
      keyAdvantage: "Excellent cash crop in Pavagada, Madhugiri, and Koratagere red soils. Adds nitrogen to soil via root nodules.",
      recommendationSummary: "Highly remunerative if dry spells do not coincide with peg entry stage; Gypsum application mandatory."
    }
  },

  {
    id: "pigeonpea-brg2",
    name: "Pigeon Pea (Red Gram / Tur)",
    kannadaName: "ತೊಗರಿ",
    scientificName: "Cajanus cajan",
    popularVarieties: ["BRG-1", "BRG-2", "BRG-5", "TS-3R"],
    season: "kharif",
    cropDurationDays: 160,
    sowingWindow: "June 15th to July 15th",
    harvestWindow: "December 15th to January 25th",
    category: "pulses",

    soilSuitability: {
      suitableTextures: ["red_loam", "clay_loam", "black_soil", "red_sandy_loam"],
      phMin: 6.2,
      phMax: 8.2,
      optimalPh: 7.0,
      soilDepthRequired: "deep", // Deep taproot system
      drainageRequirements: ["good", "well_drained"],
      droughtTolerance: "very_high",
      waterloggingTolerance: "very_low"
    },
    waterRequirements: {
      totalMm: 600,
      minRainfallMm: 480,
      sensitivity: "low",
      irrigationNeeds: "Tolerates extended dry spells; 1 critical irrigation during pod development increases yield by 40%."
    },
    climateRequirements: {
      minTempC: 18,
      maxTempC: 38,
      optimalTempC: 28
    },

    yieldPerAcre: {
      pessimistic: 5,
      expected: 8,
      optimistic: 12
    },

    cultivationCostPerAcre: {
      landPreparation: 2800,
      seeds: 900,
      farmyardManure: 2800,
      fertilizers: 2100,      // Rhizobium inoculant, DAP, Sulphur
      sowingAndTransplanting: 1800,
      weedingAndIntercultivation: 2400,
      plantProtection: 2800,  // Pod borer spray rounds are critical
      harvestingAndThreshing: 3600,
      postHarvestTransport: 800,
      total: 20000
    },

    pricePerQuintal: {
      msp: 7550,
      pessimistic: 6800,
      expected: 8400,
      optimistic: 9800
    },

    pestsAndDiseases: [
      {
        name: "Pod Borer (Helicoverpa armigera)",
        riskLevel: "High",
        symptoms: "Bored holes in buds, flowers, and developing pods.",
        management: "Pheromone traps (4/acre); spray Chlorantraniliprole 18.5 SC @ 0.3 ml/L at 50% flowering."
      },
      {
        name: "Fusarium Wilt",
        riskLevel: "Moderate",
        symptoms: "Gradual drooping and yellowing of foliage followed by whole plant death.",
        management: "Use wilt-resistant cultivars like BRG-2 / TS-3R; seed treat with Trichoderma."
      }
    ],

    localGuidance: {
      source: "UAS Bangalore Pulse Research Station",
      keyAdvantage: "Deep taproot breaks hard subsoil pan and mines residual nutrients. High market demand in Karnataka mandis.",
      recommendationSummary: "Excellent standalone or intercrop with Ragi (8:2 or 4:2 ratio) for risk mitigation."
    }
  },

  {
    id: "chickpea-jg11",
    name: "Chickpea (Bengal Gram)",
    kannadaName: "ಕಡಲೆ",
    scientificName: "Cicer arietinum",
    popularVarieties: ["JG-11", "JAKI-9218", "BGD-103", "KAK-2"],
    season: "rabi",
    cropDurationDays: 95,
    sowingWindow: "October 1st to November 10th",
    harvestWindow: "January 15th to February 25th",
    category: "pulses",

    soilSuitability: {
      suitableTextures: ["black_soil", "clay_loam", "medium_black", "loam"],
      phMin: 6.5,
      phMax: 8.5,
      optimalPh: 7.4,
      soilDepthRequired: "medium",
      drainageRequirements: ["good", "moderate"],
      droughtTolerance: "high",
      waterloggingTolerance: "very_low"
    },
    waterRequirements: {
      totalMm: 350,
      minRainfallMm: 250,
      sensitivity: "low",
      irrigationNeeds: "Requires residual moisture after Kharif; 1 light sprinkler irrigation at pre-flowering boosts yield."
    },
    climateRequirements: {
      minTempC: 12,
      maxTempC: 30,
      optimalTempC: 22
    },

    yieldPerAcre: {
      pessimistic: 4.5,
      expected: 7.5,
      optimistic: 11
    },

    cultivationCostPerAcre: {
      landPreparation: 2600,
      seeds: 2800,
      farmyardManure: 1800,
      fertilizers: 1900,
      sowingAndTransplanting: 1600,
      weedingAndIntercultivation: 1600,
      plantProtection: 2100,
      harvestingAndThreshing: 3200,
      postHarvestTransport: 700,
      total: 18300
    },

    pricePerQuintal: {
      msp: 5440,
      pessimistic: 5000,
      expected: 5900,
      optimistic: 6800
    },

    pestsAndDiseases: [
      {
        name: "Gram Pod Borer",
        riskLevel: "High",
        symptoms: "Larvae feed on leaves and bore into pods.",
        management: "Install bird perches; spray Emamectin benzoate 5 SG @ 0.4 g/L."
      },
      {
        name: "Dry Root Rot (Rhizoctonia bataticola)",
        riskLevel: "Moderate",
        symptoms: "Roots become brittle and black under moisture stress conditions.",
        management: "Avoid moisture stress during pod filling; treat seed with carbendazim."
      }
    ],

    localGuidance: {
      source: "UAS Raichur & UAS Bangalore Rabi Pulse Cell",
      keyAdvantage: "Short duration Rabi pulse with low water needs. Thrives on moisture retentive soils.",
      recommendationSummary: "Best post-Kharif catch crop on black clay-loam plots in Tumakuru & Mandya."
    }
  },

  {
    id: "horsegram-phg9",
    name: "Horse Gram (Huruli)",
    kannadaName: "ಹುರುಳಿ",
    scientificName: "Macrotyloma uniflorum",
    popularVarieties: ["PHG-9", "CRIDA 18R", "KBH-1"],
    season: "rabi",
    cropDurationDays: 85,
    sowingWindow: "August 15th to September 25th",
    harvestWindow: "November 20th to December 25th",
    category: "pulses",

    soilSuitability: {
      suitableTextures: ["red_sandy_loam", "shallow_gravelly", "sandy_loam", "poor_degraded"],
      phMin: 5.0,
      phMax: 8.0,
      optimalPh: 6.2,
      soilDepthRequired: "shallow", // Grows on poorest soils
      drainageRequirements: ["moderate", "good"],
      droughtTolerance: "extreme",
      waterloggingTolerance: "low"
    },
    waterRequirements: {
      totalMm: 280,
      minRainfallMm: 200,
      sensitivity: "very_low",
      irrigationNeeds: "100% rainfed survivor crop. Requires zero irrigation once germinated."
    },
    climateRequirements: {
      minTempC: 16,
      maxTempC: 38,
      optimalTempC: 28
    },

    yieldPerAcre: {
      pessimistic: 3,
      expected: 5,
      optimistic: 7.5
    },

    cultivationCostPerAcre: {
      landPreparation: 1800,
      seeds: 600,
      farmyardManure: 1000,
      fertilizers: 1100,
      sowingAndTransplanting: 1200,
      weedingAndIntercultivation: 900,
      plantProtection: 500,
      harvestingAndThreshing: 2200,
      postHarvestTransport: 500,
      total: 9800
    },

    pricePerQuintal: {
      msp: 4800,
      pessimistic: 4200,
      expected: 5300,
      optimistic: 6400
    },

    pestsAndDiseases: [
      {
        name: "Yellow Mosaic Virus",
        riskLevel: "Low",
        symptoms: "Yellow chlorotic patches on leaves spread by whitefly.",
        management: "Spray neem oil or acetamiprid for whitefly control."
      }
    ],

    localGuidance: {
      source: "Dryland Agriculture Project, GKVK Bangalore",
      keyAdvantage: "Emergency contingency crop when Kharif sowing rains fail completely. Lowest input cost.",
      recommendationSummary: "The ultimate drought insurance crop for shallow gravelly soils."
    }
  },

  {
    id: "sorghum-m351",
    name: "Sorghum (Jowar)",
    kannadaName: "ಜೋಳ",
    scientificName: "Sorghum bicolor",
    popularVarieties: ["M 35-1 (Maldandi)", "CSV-22", "SPV-2217"],
    season: "rabi",
    cropDurationDays: 120,
    sowingWindow: "September 15th to October 20th",
    harvestWindow: "January 20th to February 28th",
    category: "grains",

    soilSuitability: {
      suitableTextures: ["black_soil", "clay_loam", "medium_deep_red"],
      phMin: 6.0,
      phMax: 8.5,
      optimalPh: 7.2,
      soilDepthRequired: "medium",
      drainageRequirements: ["moderate", "good"],
      droughtTolerance: "high",
      waterloggingTolerance: "moderate"
    },
    waterRequirements: {
      totalMm: 400,
      minRainfallMm: 320,
      sensitivity: "low",
      irrigationNeeds: "Grows well on conserved soil moisture; 1 irrigation at boot stage doubles fodder and grain yield."
    },
    climateRequirements: {
      minTempC: 15,
      maxTempC: 38,
      optimalTempC: 28
    },

    yieldPerAcre: {
      pessimistic: 7,
      expected: 12,
      optimistic: 18
    },

    cultivationCostPerAcre: {
      landPreparation: 2500,
      seeds: 800,
      farmyardManure: 2500,
      fertilizers: 2300,
      sowingAndTransplanting: 1800,
      weedingAndIntercultivation: 1600,
      plantProtection: 1100,
      harvestingAndThreshing: 3500,
      postHarvestTransport: 800,
      total: 16900
    },

    pricePerQuintal: {
      msp: 3371,
      pessimistic: 3100,
      expected: 3800,
      optimistic: 4600
    },

    pestsAndDiseases: [
      {
        name: "Shoot Fly (Atherigona soccata)",
        riskLevel: "Moderate",
        symptoms: "Larvae cause 'dead hearts' in 1-4 week old seedlings.",
        management: "Early sowing within 10 days of monsoon recession; seed treatment with Imidacloprid."
      }
    ],

    localGuidance: {
      source: "UAS Dharwad & KSDA",
      keyAdvantage: "Dual-purpose value: grain fetches good price and dry stover provides prime livestock fodder.",
      recommendationSummary: "Reliable food-and-fodder choice on black and medium-loam soils."
    }
  },

  {
    id: "sunflower-kbsh44",
    name: "Sunflower",
    kannadaName: "ಸೂರ್ಯಕಾಂತಿ",
    scientificName: "Helianthus annuus",
    popularVarieties: ["KBSH-44", "RSFH-130", "DRSH-1"],
    season: "kharif",
    cropDurationDays: 95,
    sowingWindow: "July 1st to August 10th",
    harvestWindow: "October 10th to November 15th",
    category: "oilseeds",

    soilSuitability: {
      suitableTextures: ["red_loam", "black_soil", "sandy_loam", "clay_loam"],
      phMin: 6.0,
      phMax: 8.0,
      optimalPh: 6.8,
      soilDepthRequired: "medium",
      drainageRequirements: ["good", "well_drained"],
      droughtTolerance: "high",
      waterloggingTolerance: "low"
    },
    waterRequirements: {
      totalMm: 450,
      minRainfallMm: 350,
      sensitivity: "moderate",
      irrigationNeeds: "Critical stages for irrigation are button stage, flowering, and seed development."
    },
    climateRequirements: {
      minTempC: 18,
      maxTempC: 35,
      optimalTempC: 26
    },

    yieldPerAcre: {
      pessimistic: 4.5,
      expected: 7.5,
      optimistic: 11
    },

    cultivationCostPerAcre: {
      landPreparation: 2800,
      seeds: 1800,
      farmyardManure: 2600,
      fertilizers: 2400,      // Boron application @ 2g/L essential for seed filling
      sowingAndTransplanting: 1800,
      weedingAndIntercultivation: 1900,
      plantProtection: 1400,
      harvestingAndThreshing: 3200,
      postHarvestTransport: 800,
      total: 18700
    },

    pricePerQuintal: {
      msp: 7280,
      pessimistic: 6100,
      expected: 7150,
      optimistic: 8000
    },

    pestsAndDiseases: [
      {
        name: "Alternaria Blight & Rust",
        riskLevel: "Moderate",
        symptoms: "Brown angular spots on lower leaves spreading upward.",
        management: "Foliar spray with Dithane M-45 @ 2.5 g/L."
      },
      {
        name: "Parrot & Bird Damage",
        riskLevel: "High",
        symptoms: "Seed plucking at maturity stage.",
        management: "Reflective bird ribbons; synchronous planting with neighbours."
      }
    ],

    localGuidance: {
      source: "AICRP Sunflower, GKVK Bangalore",
      keyAdvantage: "High oil content, photo-insensitive (can fit any season with soil moisture). Strong APMC demand.",
      recommendationSummary: "Good alternative oilseed to groundnut with lower seed cost."
    }
  },

  {
    id: "maize-nah1137",
    name: "Maize (Hybrid Corn)",
    kannadaName: "ಮೆಕ್ಕೆಜೋಳ",
    scientificName: "Zea mays",
    popularVarieties: ["NAH-1137 (Hema)", "Deccan 103", "NK 6240", "CP 333"],
    season: "kharif",
    cropDurationDays: 110,
    sowingWindow: "June 20th to July 31st",
    harvestWindow: "October 15th to November 25th",
    category: "grains",

    soilSuitability: {
      suitableTextures: ["red_loam", "clay_loam", "alluvial", "sandy_loam"],
      phMin: 6.0,
      phMax: 7.5,
      optimalPh: 6.8,
      soilDepthRequired: "deep",
      drainageRequirements: ["good", "well_drained"],
      droughtTolerance: "moderate",
      waterloggingTolerance: "low" // Highly sensitive to standing water
    },
    waterRequirements: {
      totalMm: 550,
      minRainfallMm: 480,
      sensitivity: "high",
      irrigationNeeds: "Tasseling and silking are moisture-critical; moisture stress at pollination cuts yield by 50%."
    },
    climateRequirements: {
      minTempC: 18,
      maxTempC: 36,
      optimalTempC: 27
    },

    yieldPerAcre: {
      pessimistic: 16,
      expected: 26,
      optimistic: 35
    },

    cultivationCostPerAcre: {
      landPreparation: 3200,
      seeds: 2200,
      farmyardManure: 3200,
      fertilizers: 3800,      // Heavy feeder of Nitrogen and Zinc
      sowingAndTransplanting: 2200,
      weedingAndIntercultivation: 2400,
      plantProtection: 2600,  // Fall Armyworm management is crucial
      harvestingAndThreshing: 4800,
      postHarvestTransport: 1400, // High tonnage transport
      total: 26600
    },

    pricePerQuintal: {
      msp: 2225,
      pessimistic: 1850,
      expected: 2280,
      optimistic: 2600
    },

    pestsAndDiseases: [
      {
        name: "Fall Armyworm (Spodoptera frugiperda)",
        riskLevel: "Critical",
        symptoms: "Shot holes, ragged leaf damage, and sawdust-like frass in leaf whorls.",
        management: "Whorl application of Sand + Lime (9:1) or spray Chlorantraniliprole / Spinetoram."
      }
    ],

    localGuidance: {
      source: "UAS Bangalore Maize Scheme",
      keyAdvantage: "Massive biomass and tonnage; instant liquidity at poultry and starch feed mills across Tumakuru & Mandya.",
      recommendationSummary: "High input, high gross volume crop. Only plant if irrigation is available or Kharif rainfall is dependable."
    }
  },

  {
    id: "sugarcane-co86032",
    name: "Sugarcane",
    kannadaName: "ಕಬ್ಬು",
    scientificName: "Saccharum officinarum",
    popularVarieties: ["Co 86032 (Nayana)", "Co 62175", "VCF 0517"],
    season: "perennial", // 12-14 month cycle
    cropDurationDays: 365,
    sowingWindow: "January to March (Eksali) or June to August",
    harvestWindow: "12 to 14 months after planting",
    category: "cash_commercial",

    soilSuitability: {
      suitableTextures: ["clay_loam", "alluvial", "deep_red_loam", "black_soil"],
      phMin: 6.5,
      phMax: 8.0,
      optimalPh: 7.0,
      soilDepthRequired: "deep",
      drainageRequirements: ["good", "moderate"],
      droughtTolerance: "low",
      waterloggingTolerance: "moderate"
    },
    waterRequirements: {
      totalMm: 1800,
      minRainfallMm: 1200,
      sensitivity: "very_high",
      irrigationNeeds: "Requires perennial canal flow (e.g., VC Canal from KRS) or high-yield borewells. Minimum 25-30 irrigations."
    },
    climateRequirements: {
      minTempC: 20,
      maxTempC: 40,
      optimalTempC: 30
    },

    yieldPerAcre: {
      pessimistic: 32,   // 32 tonnes
      expected: 45,     // 45 tonnes
      optimistic: 60    // 60 tonnes
    },

    cultivationCostPerAcre: {
      landPreparation: 5500,
      seeds: 8500,            // 35,000 two-budded setts
      farmyardManure: 7000,
      fertilizers: 9500,      // High NPK + micronutrients
      sowingAndTransplanting: 5500,
      weedingAndIntercultivation: 6500,
      plantProtection: 3500,
      harvestingAndThreshing: 16000, // Factory cutting & loading charges
      postHarvestTransport: 4500,
      total: 66500
    },

    // Sugarcane priced per Tonne (FRP)
    pricePerQuintal: {
      msp: 340,         // ₹3,400 per Tonne (₹340/quintal) Fair & Remunerative Price
      pessimistic: 310,
      expected: 345,
      optimistic: 380
    },

    pestsAndDiseases: [
      {
        name: "Early Shoot Borer & Inter-node Borer",
        riskLevel: "High",
        symptoms: "Dead hearts in young shoots; bore holes on rind with sawdust frass.",
        management: "Release Trichogramma chilonis egg parasitoids @ 2.5 cc/acre."
      },
      {
        name: "Red Rot (Colletotrichum falcatum)",
        riskLevel: "High",
        symptoms: "Spindle leaves wither; split stalks show red discoloration with white cross patches.",
        management: "Use healthy certified setts; avoid ratoon of infected crop."
      }
    ],

    localGuidance: {
      source: "Zonal Agricultural Research Station (VC Farm), Mandya",
      keyAdvantage: "Assured purchase tie-up with sugar mills (e.g. MySugar, Chamundeshwari Sugars). High revenue if canal water is guaranteed.",
      recommendationSummary: "Strictly for canal command areas or abundant borewells; financially ruinous if water dries up midway."
    }
  },

  {
    id: "paddy-ir64",
    name: "Paddy (Wetland Rice)",
    kannadaName: "ಭತ್ತ",
    scientificName: "Oryza sativa",
    popularVarieties: ["IR-64", "Jyothi", "BPT-5204 (Sona Masuri)", "Tanvi"],
    season: "kharif",
    cropDurationDays: 135,
    sowingWindow: "July 1st to August 10th",
    harvestWindow: "November 15th to December 25th",
    category: "grains",

    soilSuitability: {
      suitableTextures: ["clay_loam", "clay", "silty_clay", "alluvial"],
      phMin: 5.5,
      phMax: 7.8,
      optimalPh: 6.5,
      soilDepthRequired: "medium",
      drainageRequirements: ["poor", "moderate", "slow_draining"],
      droughtTolerance: "very_low",
      waterloggingTolerance: "extreme" // Requires standing water
    },
    waterRequirements: {
      totalMm: 1200,
      minRainfallMm: 900,
      sensitivity: "extreme",
      irrigationNeeds: "Requires continuous ponded water (5 cm depth) or AWD (Alternate Wetting and Drying) canal rotation."
    },
    climateRequirements: {
      minTempC: 20,
      maxTempC: 36,
      optimalTempC: 28
    },

    yieldPerAcre: {
      pessimistic: 18,
      expected: 25,
      optimistic: 32
    },

    cultivationCostPerAcre: {
      landPreparation: 4200,  // Puddling & bund trimming
      seeds: 1200,
      farmyardManure: 3500,
      fertilizers: 3600,
      sowingAndTransplanting: 4500, // Manual transplanting gang
      weedingAndIntercultivation: 2400,
      plantProtection: 2200,
      harvestingAndThreshing: 4800, // Combine harvester
      postHarvestTransport: 1200,
      total: 27600
    },

    pricePerQuintal: {
      msp: 2320,        // Grade-A Paddy MSP
      pessimistic: 2000,
      expected: 2450,
      optimistic: 2900  // Premium for Sona Masuri (BPT 5204)
    },

    pestsAndDiseases: [
      {
        name: "Brown Plant Hopper (BPH)",
        riskLevel: "High",
        symptoms: "Circular patches of drying called 'hopper burn' in flooded fields.",
        management: "Drain water for 3-4 days; spray Pymetrozine 50 WG @ 0.6 g/L."
      },
      {
        name: "Blast & Sheath Blight",
        riskLevel: "Moderate",
        symptoms: "Eye-shaped lesions on leaves; rotting of leaf sheaths near water line.",
        management: "Avoid excess nitrogen; foliar spray of Trifloxystrobin + Tebuconazole."
      }
    ],

    localGuidance: {
      source: "Mandya VC Farm & KSDA",
      keyAdvantage: "Staple grain with immediate mandi procurement and guaranteed MSP payment.",
      recommendationSummary: "Only recommended on canal-irrigated plots with heavy, moisture-holding clay soil."
    }
  }
];
