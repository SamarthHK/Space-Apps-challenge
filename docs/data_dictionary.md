# Data dictionary

The platform stores raw source responses separately from normalized observations.
Canonical variables and units are defined in [`config/variables.yaml`](../config/variables.yaml).

Every normalized observation has a field, variable, measurement type, source, unit,
time (when applicable), depth (for soil), statistic, and quality flag. Soil depth
intervals are retained in centimetres; climate dates are stored as daily timestamps;
spectral indices are dimensionless values bounded to `[-1, 1]`.

Missing data is not represented as zero. Use a quality or missing-value reason such
as `NOT_AVAILABLE_FROM_SOURCE`, `OUTSIDE_SOURCE_COVERAGE`, or `ACCESS_RESTRICTED`.
