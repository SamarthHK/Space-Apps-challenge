/**
 * Karnataka Agricultural Market Intelligence Dataset
 * Focus Mandis: Tumakuru APMC, Tiptur APMC, Mandya APMC, Bengaluru (Yeshwantpur) APMC, Ramanagara APMC
 * Integration Reference: AGMARKNET (Directorate of Marketing & Inspection, GoI) & eNAM
 */

export const karnatakaMandis = [
  {
    id: "mandi-tumakuru",
    name: "Tumakuru APMC Yard",
    kannadaName: "ತುಮಕೂರು ಎ.ಪಿ.ಎಂ.ಸಿ",
    district: "Tumakuru",
    taluk: "Tumakuru",
    coordinates: [13.342, 77.101],
    marketType: "Principal Market Yard (Class A)",
    eNamEnabled: true,
    avgTransportRatePerKmQuintal: 4.5, // ₹4.50 per quintal per km
    mandiCessPct: 1.5, // 1.5% APMC market cess
    majorArrivals: ["ragi-gpu28", "groundnut-tmv2", "pigeonpea-brg2", "maize-nah1137"]
  },
  {
    id: "mandi-tiptur",
    name: "Tiptur APMC (Copra & Oilseeds Hub)",
    kannadaName: "ತಿಪಟೂರು ಎ.ಪಿ.ಎಂ.ಸಿ",
    district: "Tumakuru",
    taluk: "Tiptur",
    coordinates: [13.255, 76.478],
    marketType: "Specialized Commodity Hub",
    eNamEnabled: true,
    avgTransportRatePerKmQuintal: 4.8,
    mandiCessPct: 1.5,
    majorArrivals: ["groundnut-tmv2", "sunflower-kbsh44", "ragi-gpu28"]
  },
  {
    id: "mandi-mandya",
    name: "Mandya APMC Yard (Bandigowda Layout)",
    kannadaName: "ಮಂಡ್ಯ ಎ.ಪಿ.ಎಂ.ಸಿ",
    district: "Mandya",
    taluk: "Mandya",
    coordinates: [12.528, 76.903],
    marketType: "Principal Market Yard",
    eNamEnabled: true,
    avgTransportRatePerKmQuintal: 4.2,
    mandiCessPct: 1.5,
    majorArrivals: ["paddy-ir64", "sugarcane-co86032", "ragi-gpu28"]
  },
  {
    id: "mandi-bengaluru",
    name: "Bengaluru (Yeshwantpur) APMC Yard",
    kannadaName: "ಬೆಂಗಳೂರು ಯಶವಂತಪುರ ಎ.ಪಿ.ಎಂ.ಸಿ",
    district: "Bengaluru Urban",
    taluk: "Bengaluru North",
    coordinates: [13.023, 77.549],
    marketType: "Apex Terminal Market",
    eNamEnabled: true,
    avgTransportRatePerKmQuintal: 5.5,
    mandiCessPct: 1.75,
    majorArrivals: ["ragi-gpu28", "pigeonpea-brg2", "groundnut-tmv2", "maize-nah1137", "sunflower-kbsh44"]
  },
  {
    id: "mandi-ramanagara",
    name: "Ramanagara APMC Yard",
    kannadaName: "ರಾಮನಗರ ಎ.ಪಿ.ಎಂ.ಸಿ",
    district: "Ramanagara",
    taluk: "Ramanagara",
    coordinates: [12.715, 77.281],
    marketType: "Secondary Market Yard",
    eNamEnabled: false,
    avgTransportRatePerKmQuintal: 4.6,
    mandiCessPct: 1.5,
    majorArrivals: ["ragi-gpu28", "pigeonpea-brg2", "horsegram-phg9"]
  }
];

export const commodityMarketPrices = {
  "ragi-gpu28": {
    cropName: "Finger Millet (Ragi)",
    kannadaName: "ರಾಗಿ",
    unit: "₹ / Quintal (100 kg)",
    mspSupportPrice: 4290,
    mandiReports: [
      {
        mandiId: "mandi-tumakuru",
        mandiName: "Tumakuru APMC",
        minPrice: 3800,
        modalPrice: 4350,
        maxPrice: 4650,
        dailyArrivalsQuintals: 420,
        trend: "stable",
        dataSource: "AGMARKNET Daily Bulletin"
      },
      {
        mandiId: "mandi-tiptur",
        mandiName: "Tiptur APMC",
        minPrice: 3750,
        modalPrice: 4280,
        maxPrice: 4500,
        dailyArrivalsQuintals: 195,
        trend: "up",
        dataSource: "AGMARKNET Daily Bulletin"
      },
      {
        mandiId: "mandi-mandya",
        mandiName: "Mandya APMC",
        minPrice: 3900,
        modalPrice: 4400,
        maxPrice: 4700,
        dailyArrivalsQuintals: 280,
        trend: "up",
        dataSource: "AGMARKNET Daily Bulletin"
      },
      {
        mandiId: "mandi-bengaluru",
        mandiName: "Bengaluru (Yeshwantpur) APMC",
        minPrice: 4100,
        modalPrice: 4600,
        maxPrice: 4950,
        dailyArrivalsQuintals: 850,
        trend: "up",
        dataSource: "e-NAM Karnataka Gateway"
      }
    ],
    seasonalTrendMonths: [
      { month: "Jun", modalPrice: 4400, arrivals: 120 },
      { month: "Jul", modalPrice: 4520, arrivals: 90 },
      { month: "Aug", modalPrice: 4600, arrivals: 80 },
      { month: "Sep", modalPrice: 4580, arrivals: 95 },
      { month: "Oct", modalPrice: 4450, arrivals: 180 },
      { month: "Nov", modalPrice: 4100, arrivals: 720 }, // Post-harvest arrival glut
      { month: "Dec", modalPrice: 4050, arrivals: 850 },
      { month: "Jan", modalPrice: 4200, arrivals: 580 },
      { month: "Feb", modalPrice: 4350, arrivals: 340 }
    ],
    farmGatePriceDeductions: {
      baggingPerQuintal: 45,
      weighingLaborPerQuintal: 35,
      mandiCessPercentage: 1.5,
      avgTransportDistanceKm: 25,
      estFarmGatePrice: 4120
    }
  },

  "groundnut-tmv2": {
    cropName: "Groundnut (Pods)",
    kannadaName: "ಕಡಲೆಕಾಯಿ",
    unit: "₹ / Quintal",
    mspSupportPrice: 6783,
    mandiReports: [
      {
        mandiId: "mandi-tumakuru",
        mandiName: "Tumakuru APMC",
        minPrice: 6200,
        modalPrice: 6900,
        maxPrice: 7450,
        dailyArrivalsQuintals: 310,
        trend: "up",
        dataSource: "AGMARKNET Daily Bulletin"
      },
      {
        mandiId: "mandi-tiptur",
        mandiName: "Tiptur APMC",
        minPrice: 6350,
        modalPrice: 7100,
        maxPrice: 7600,
        dailyArrivalsQuintals: 520,
        trend: "up",
        dataSource: "AGMARKNET Daily Bulletin"
      },
      {
        mandiId: "mandi-bengaluru",
        mandiName: "Bengaluru (Yeshwantpur) APMC",
        minPrice: 6500,
        modalPrice: 7350,
        maxPrice: 7850,
        dailyArrivalsQuintals: 460,
        trend: "stable",
        dataSource: "e-NAM Karnataka Gateway"
      }
    ],
    seasonalTrendMonths: [
      { month: "Jun", modalPrice: 7200, arrivals: 60 },
      { month: "Jul", modalPrice: 7350, arrivals: 45 },
      { month: "Aug", modalPrice: 7400, arrivals: 40 },
      { month: "Sep", modalPrice: 7250, arrivals: 90 },
      { month: "Oct", modalPrice: 6600, arrivals: 480 },
      { month: "Nov", modalPrice: 6450, arrivals: 650 },
      { month: "Dec", modalPrice: 6700, arrivals: 390 },
      { month: "Jan", modalPrice: 6900, arrivals: 280 }
    ],
    farmGatePriceDeductions: {
      baggingPerQuintal: 50,
      weighingLaborPerQuintal: 40,
      mandiCessPercentage: 1.5,
      avgTransportDistanceKm: 28,
      estFarmGatePrice: 6580
    }
  },

  "pigeonpea-brg2": {
    cropName: "Pigeon Pea (Red Gram / Tur)",
    kannadaName: "ತೊಗರಿ",
    unit: "₹ / Quintal",
    mspSupportPrice: 7550,
    mandiReports: [
      {
        mandiId: "mandi-tumakuru",
        mandiName: "Tumakuru APMC",
        minPrice: 7600,
        modalPrice: 8450,
        maxPrice: 9100,
        dailyArrivalsQuintals: 160,
        trend: "up",
        dataSource: "AGMARKNET Daily Bulletin"
      },
      {
        mandiId: "mandi-bengaluru",
        mandiName: "Bengaluru (Yeshwantpur) APMC",
        minPrice: 8100,
        modalPrice: 8900,
        maxPrice: 9600,
        dailyArrivalsQuintals: 580,
        trend: "up",
        dataSource: "e-NAM Karnataka Gateway"
      }
    ],
    seasonalTrendMonths: [
      { month: "Aug", modalPrice: 8800, arrivals: 30 },
      { month: "Sep", modalPrice: 9100, arrivals: 25 },
      { month: "Oct", modalPrice: 9300, arrivals: 20 },
      { month: "Nov", modalPrice: 8900, arrivals: 50 },
      { month: "Dec", modalPrice: 8200, arrivals: 220 },
      { month: "Jan", modalPrice: 7900, arrivals: 410 },
      { month: "Feb", modalPrice: 8300, arrivals: 280 }
    ],
    farmGatePriceDeductions: {
      baggingPerQuintal: 50,
      weighingLaborPerQuintal: 40,
      mandiCessPercentage: 1.5,
      avgTransportDistanceKm: 30,
      estFarmGatePrice: 8090
    }
  },

  "chickpea-jg11": {
    cropName: "Chickpea (Bengal Gram)",
    kannadaName: "ಕಡಲೆ",
    unit: "₹ / Quintal",
    mspSupportPrice: 5440,
    mandiReports: [
      {
        mandiId: "mandi-tumakuru",
        mandiName: "Tumakuru APMC",
        minPrice: 5200,
        modalPrice: 5900,
        maxPrice: 6300,
        dailyArrivalsQuintals: 180,
        trend: "stable",
        dataSource: "AGMARKNET Daily Bulletin"
      },
      {
        mandiId: "mandi-bengaluru",
        mandiName: "Bengaluru (Yeshwantpur) APMC",
        minPrice: 5500,
        modalPrice: 6200,
        maxPrice: 6700,
        dailyArrivalsQuintals: 420,
        trend: "stable",
        dataSource: "e-NAM Karnataka Gateway"
      }
    ],
    seasonalTrendMonths: [
      { month: "Dec", modalPrice: 6200, arrivals: 40 },
      { month: "Jan", modalPrice: 5800, arrivals: 240 },
      { month: "Feb", modalPrice: 5600, arrivals: 380 },
      { month: "Mar", modalPrice: 5750, arrivals: 260 }
    ],
    farmGatePriceDeductions: {
      baggingPerQuintal: 45,
      weighingLaborPerQuintal: 35,
      mandiCessPercentage: 1.5,
      avgTransportDistanceKm: 25,
      estFarmGatePrice: 5620
    }
  },

  "maize-nah1137": {
    cropName: "Maize (Hybrid Yellow)",
    kannadaName: "ಮೆಕ್ಕೆಜೋಳ",
    unit: "₹ / Quintal",
    mspSupportPrice: 2225,
    mandiReports: [
      {
        mandiId: "mandi-tumakuru",
        mandiName: "Tumakuru APMC",
        minPrice: 2050,
        modalPrice: 2280,
        maxPrice: 2420,
        dailyArrivalsQuintals: 780,
        trend: "stable",
        dataSource: "AGMARKNET Daily Bulletin"
      },
      {
        mandiId: "mandi-mandya",
        mandiName: "Mandya APMC",
        minPrice: 2000,
        modalPrice: 2240,
        maxPrice: 2390,
        dailyArrivalsQuintals: 340,
        trend: "down",
        dataSource: "AGMARKNET Daily Bulletin"
      }
    ],
    seasonalTrendMonths: [
      { month: "Aug", modalPrice: 2400, arrivals: 90 },
      { month: "Sep", modalPrice: 2380, arrivals: 120 },
      { month: "Oct", modalPrice: 2150, arrivals: 920 },
      { month: "Nov", modalPrice: 2100, arrivals: 1150 },
      { month: "Dec", modalPrice: 2220, arrivals: 650 }
    ],
    farmGatePriceDeductions: {
      baggingPerQuintal: 40,
      weighingLaborPerQuintal: 30,
      mandiCessPercentage: 1.5,
      avgTransportDistanceKm: 20,
      estFarmGatePrice: 2110
    }
  },

  "paddy-ir64": {
    cropName: "Paddy (Common / Sona Masuri)",
    kannadaName: "ಭತ್ತ",
    unit: "₹ / Quintal",
    mspSupportPrice: 2320,
    mandiReports: [
      {
        mandiId: "mandi-mandya",
        mandiName: "Mandya APMC",
        minPrice: 2250,
        modalPrice: 2520,
        maxPrice: 2850,
        dailyArrivalsQuintals: 950,
        trend: "stable",
        dataSource: "AGMARKNET Daily Bulletin"
      },
      {
        mandiId: "mandi-tumakuru",
        mandiName: "Tumakuru APMC",
        minPrice: 2180,
        modalPrice: 2440,
        maxPrice: 2750,
        dailyArrivalsQuintals: 310,
        trend: "stable",
        dataSource: "AGMARKNET Daily Bulletin"
      }
    ],
    seasonalTrendMonths: [
      { month: "Oct", modalPrice: 2600, arrivals: 180 },
      { month: "Nov", modalPrice: 2350, arrivals: 1100 },
      { month: "Dec", modalPrice: 2380, arrivals: 1400 },
      { month: "Jan", modalPrice: 2480, arrivals: 750 }
    ],
    farmGatePriceDeductions: {
      baggingPerQuintal: 45,
      weighingLaborPerQuintal: 35,
      mandiCessPercentage: 1.5,
      avgTransportDistanceKm: 18,
      estFarmGatePrice: 2330
    }
  }
};
