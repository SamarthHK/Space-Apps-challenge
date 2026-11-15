# Source catalog

| Adapter | Domain | Default behavior |
|---|---|---|
| SoilGrids 2.0 | Soil | REST point query with local synthetic fallback |
| NASA POWER | Climate | Daily point query with local synthetic fallback |
| Sentinel-2 adapter | Historical land | Repeat-scene simulation until Earth Engine credentials are configured |
| CGWB adapter | Water | Nearest reference-well match |
| EcoCrop | Crop requirements | YAML crop catalog |
| FAOSTAT adapter | Crop performance | Regional benchmark catalog |

The YAML registry is authoritative for source metadata and canonical variables.
Adapters preserve raw responses before normalization. Authentication-required or
unavailable datasets should be marked as missing rather than substituted silently;
the synthetic adapters are explicitly documented in generated reports.
