/**
 * Crop Recommendation Engine — Transparent Rule-Based Agronomic & Financial System
 * Tailored for Karnataka Farmers (Tumakuru & Mandya Agro-Ecological Zones)
 */

import { karnatakaCrops } from '../data/karnatakaCrops.js';
import { districtClimateBaselines } from '../data/environmentalData.js';

export const recommendationEngine = {
  /**
   * Run full recommendation pipeline for a specific plot and target season
   * @param {Object} plot - The farmer's registered plot object
   * @param {string} targetSeason - 'kharif' | 'rabi' | 'summer' | 'any'
   * @param {Object} priceCostAdjustments - Optional sensitivity overrides { priceDeltaPct, costDeltaPct }
   */
  evaluatePlot(plot, targetSeason = "kharif", priceCostAdjustments = { priceDeltaPct: 0, costDeltaPct: 0 }) {
    const climate = districtClimateBaselines[plot.district] || districtClimateBaselines["Tumakuru"];
    const soil = plot.soilRecord || {};
    const water = plot.waterRecord || {};

    const results = karnatakaCrops.map(crop => {
      // -----------------------------------------------------------------
      // STAGE A: AGRONOMIC FILTERING (Hard Agricultural Constraints)
      // -----------------------------------------------------------------
      const agronomicCheck = this.checkAgronomicSuitability(crop, plot, soil, water, climate, targetSeason);

      // -----------------------------------------------------------------
      // STAGE B & C: FINANCIAL RANKING & SCENARIO MODELING
      // -----------------------------------------------------------------
      const financials = this.calculateCropFinancials(crop, plot.areaAcre, priceCostAdjustments);

      return {
        crop,
        isSuitable: agronomicCheck.isSuitable,
        suitabilityScore: agronomicCheck.score, // 0 - 100
        agronomicDisqualifiers: agronomicCheck.disqualifiers,
        agronomicWarnings: agronomicCheck.warnings,
        agronomicMatches: agronomicCheck.matches,
        financials
      };
    });

    // Partition into suitable and disqualified
    const suitableCrops = results
      .filter(r => r.isSuitable)
      .sort((a, b) => b.financials.expected.netReturnPerAcre - a.financials.expected.netReturnPerAcre);

    const disqualifiedCrops = results
      .filter(r => !r.isSuitable)
      .sort((a, b) => b.suitabilityScore - a.suitabilityScore);

    return {
      plotId: plot.id,
      plotName: plot.name,
      plotAreaAcre: plot.areaAcre,
      targetSeason,
      suitableCount: suitableCrops.length,
      disqualifiedCount: disqualifiedCrops.length,
      recommendations: suitableCrops,
      disqualified: disqualifiedCrops,
      evaluatedAt: new Date().toISOString()
    };
  },

  /**
   * Stage A: Verify physical soil, water, climate, and seasonal constraints
   */
  checkAgronomicSuitability(crop, plot, soil, water, climate, targetSeason) {
    const disqualifiers = [];
    const warnings = [];
    const matches = [];
    let score = 100;

    // 1. Season Compatibility
    if (targetSeason !== "any") {
      if (crop.season !== "perennial" && crop.season !== targetSeason) {
        disqualifiers.push(`Crop season (${crop.season.toUpperCase()}) does not match selected planting season (${targetSeason.toUpperCase()}).`);
        score -= 50;
      } else {
        matches.push(`Matches target season (${crop.season.toUpperCase()}).`);
      }
    }

    // 2. Water & Irrigation Source Feasibility
    const isRainfed = plot.irrigationType === "rainfed";
    const hasPerennialWater = plot.waterAvailability === "high_perennial" || plot.irrigationType === "canal" || plot.irrigationType === "borewell";

    if (crop.waterRequirements.totalMm > 1000) {
      // High water crops (Paddy, Sugarcane)
      if (isRainfed) {
        disqualifiers.push(`Water requirement of ${crop.waterRequirements.totalMm} mm cannot be met on a rainfed plot (Annual rainfall ~${climate.annualRainfallMm} mm).`);
        score -= 60;
      } else if (plot.waterAvailability === "low_critical") {
        disqualifiers.push(`Requires assured perennial irrigation; plot water availability is rated critical.`);
        score -= 50;
      } else {
        matches.push(`Assured water supply (${plot.irrigationType}) satisfies high water requirement (${crop.waterRequirements.totalMm} mm).`);
      }
    } else if (crop.waterRequirements.totalMm > 500 && isRainfed) {
      warnings.push(`Moderately water sensitive (${crop.waterRequirements.totalMm} mm). Dry spells longer than 14 days during critical flowering may reduce yield.`);
      score -= 15;
    } else {
      matches.push(`Water requirement (${crop.waterRequirements.totalMm} mm) aligns with rainfall/irrigation capacity.`);
    }

    // 3. Soil pH Suitability
    const plotPh = soil.ph || 6.5; // fallback baseline if soil test missing
    if (plotPh < crop.soilSuitability.phMin) {
      disqualifiers.push(`Soil pH (${plotPh}) is too acidic for this crop (Minimum tolerated: ${crop.soilSuitability.phMin}). Lime treatment required.`);
      score -= 30;
    } else if (plotPh > crop.soilSuitability.phMax) {
      disqualifiers.push(`Soil pH (${plotPh}) is too alkaline (Maximum tolerated: ${crop.soilSuitability.phMax}). Gypsum treatment required.`);
      score -= 30;
    } else {
      matches.push(`Soil pH (${plotPh}) is within optimal tolerance (${crop.soilSuitability.phMin} - ${crop.soilSuitability.phMax}).`);
    }

    // 4. Soil Texture & Drainage Feasibility
    const plotTexture = soil.texture || "red_sandy_loam";
    const suitableTextures = crop.soilSuitability.suitableTextures || [];
    if (!suitableTextures.includes(plotTexture)) {
      if (crop.id.includes("groundnut") && (plotTexture === "clay" || plotTexture === "heavy_black")) {
        disqualifiers.push(`Heavy clay soil severely hinders groundnut gynophore peg penetration and pod formation.`);
        score -= 40;
      } else if (crop.id.includes("paddy") && (plotTexture === "sandy" || plotTexture === "loamy_sand")) {
        disqualifiers.push(`Paddy cannot maintain flooded condition on high-permeability sandy soil.`);
        score -= 50;
      } else {
        warnings.push(`Soil texture '${soil.textureDisplay || plotTexture}' is sub-optimal; requires increased organic matter/FYM.`);
        score -= 12;
      }
    } else {
      matches.push(`Soil texture '${soil.textureDisplay || plotTexture}' is suitable.`);
    }

    // 5. Soil Depth
    const plotDepth = soil.soilDepth || "medium";
    if (crop.soilSuitability.soilDepthRequired === "deep" && plotDepth === "shallow") {
      warnings.push(`Crop has a deep taproot; shallow soil depth (< 30 cm) may restrict root anchorage and moisture extraction.`);
      score -= 15;
    }

    const isSuitable = disqualifiers.length === 0;
    return {
      isSuitable,
      score: Math.max(0, Math.min(100, score)),
      disqualifiers,
      warnings,
      matches
    };
  },

  /**
   * Stage B & C: Calculate detailed net returns under 3 scenarios & user sensitivity adjustments
   */
  calculateCropFinancials(crop, acreage = 1.0, adjustments = { priceDeltaPct: 0, costDeltaPct: 0 }) {
    const baseCost = crop.cultivationCostPerAcre.total;
    const priceDelta = (adjustments.priceDeltaPct || 0) / 100;
    const costDelta = (adjustments.costDeltaPct || 0) / 100;

    // Adjusted base cost per acre
    const costPerAcre = Math.round(baseCost * (1 + costDelta));
    const totalPlotCost = Math.round(costPerAcre * acreage);

    // Scenario 1: Expected Scenario (Modal baseline)
    const expectedYield = crop.yieldPerAcre.expected;
    const expectedPrice = Math.round(crop.pricePerQuintal.expected * (1 + priceDelta));
    const expectedGrossRevenuePerAcre = Math.round(expectedYield * expectedPrice);
    const expectedNetReturnPerAcre = expectedGrossRevenuePerAcre - costPerAcre;
    const expectedTotalPlotGross = Math.round(expectedGrossRevenuePerAcre * acreage);
    const expectedTotalPlotNet = Math.round(expectedNetReturnPerAcre * acreage);

    // Scenario 2: Pessimistic Scenario (Adverse weather / -20% yield, -15% price glut, +10% pest damage cost)
    const pessimisticYield = crop.yieldPerAcre.pessimistic;
    const pessimisticPrice = Math.round(crop.pricePerQuintal.pessimistic * (1 + priceDelta * 0.8));
    const pessimisticCostPerAcre = Math.round(costPerAcre * 1.08); // extra protective sprays
    const pessimisticGrossPerAcre = Math.round(pessimisticYield * pessimisticPrice);
    const pessimisticNetPerAcre = pessimisticGrossPerAcre - pessimisticCostPerAcre;
    const pessimisticTotalPlotNet = Math.round(pessimisticNetPerAcre * acreage);

    // Scenario 3: Optimistic Scenario (Bumper harvest +15% yield, off-season price premium +10%)
    const optimisticYield = crop.yieldPerAcre.optimistic;
    const optimisticPrice = Math.round(crop.pricePerQuintal.optimistic * (1 + priceDelta * 1.2));
    const optimisticGrossPerAcre = Math.round(optimisticYield * optimisticPrice);
    const optimisticNetPerAcre = optimisticGrossPerAcre - costPerAcre;
    const optimisticTotalPlotNet = Math.round(optimisticNetPerAcre * acreage);

    // Benefit-Cost Ratio (BCR)
    const bcr = costPerAcre > 0 ? (expectedGrossRevenuePerAcre / costPerAcre).toFixed(2) : 0;

    return {
      acreage,
      cultivationCostPerAcre: costPerAcre,
      totalPlotCost,
      costBreakdown: crop.cultivationCostPerAcre,

      expected: {
        yieldPerAcre: expectedYield,
        totalPlotYield: (expectedYield * acreage).toFixed(1),
        pricePerQuintal: expectedPrice,
        grossRevenuePerAcre: expectedGrossRevenuePerAcre,
        netReturnPerAcre: expectedNetReturnPerAcre,
        totalPlotGrossRevenue: expectedTotalPlotGross,
        totalPlotNetReturn: expectedTotalPlotNet,
        bcr
      },

      pessimistic: {
        yieldPerAcre: pessimisticYield,
        totalPlotYield: (pessimisticYield * acreage).toFixed(1),
        pricePerQuintal: pessimisticPrice,
        grossRevenuePerAcre: pessimisticGrossPerAcre,
        netReturnPerAcre: pessimisticNetPerAcre,
        totalPlotNetReturn: pessimisticTotalPlotNet
      },

      optimistic: {
        yieldPerAcre: optimisticYield,
        totalPlotYield: (optimisticYield * acreage).toFixed(1),
        pricePerQuintal: optimisticPrice,
        grossRevenuePerAcre: optimisticGrossPerAcre,
        netReturnPerAcre: optimisticNetPerAcre,
        totalPlotNetReturn: optimisticTotalPlotNet
      }
    };
  }
};
