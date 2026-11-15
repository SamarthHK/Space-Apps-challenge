# Methodology and limitations

Field area and perimeter are calculated after projecting each plot to a local UTM
CRS. Soil values retain depth intervals. Climate indicators are calculated from
daily records, while vegetation metrics are derived from dated spectral-index
scenes. Suitability combines component response curves with a limiting-factor
term; rotation scores come from the configured crop-pair catalog.

The current prototype is designed for reproducibility and data plumbing. Synthetic
fallbacks, regional benchmarks, nearest-well estimates, and uncalibrated
pedotransfer/decomposition models must be replaced or validated before operational
farm decisions. Economics and profitability are intentionally out of scope.
