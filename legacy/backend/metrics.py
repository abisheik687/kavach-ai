from prometheus_client import Counter, Histogram, Gauge

DETECTIONS_TOTAL = Counter(
<<<<<<< HEAD
    "kavach_detections_total",
=======
    "mmdds_detections_total",
>>>>>>> 7df14d1 (UI enhanced)
    "Total number of detection requests processed",
    ["source", "tier"]
)

MODEL_LATENCY = Histogram(
<<<<<<< HEAD
    "kavach_model_latency_seconds",
=======
    "mmdds_model_latency_seconds",
>>>>>>> 7df14d1 (UI enhanced)
    "Latency of individual model inference",
    ["model_name"]
)

CACHE_HITS = Counter(
<<<<<<< HEAD
    "kavach_cache_hits_total",
=======
    "mmdds_cache_hits_total",
>>>>>>> 7df14d1 (UI enhanced)
    "Total number of cache hits for detection requests"
)

CONFIDENCE_HISTOGRAM = Histogram(
<<<<<<< HEAD
    "kavach_confidence_score",
=======
    "mmdds_confidence_score",
>>>>>>> 7df14d1 (UI enhanced)
    "Distribution of confidence scores",
    ["verdict"]
)

ACTIVE_SCANS = Gauge(
<<<<<<< HEAD
    "kavach_active_scans",
=======
    "mmdds_active_scans",
>>>>>>> 7df14d1 (UI enhanced)
    "Number of currently active scan requests"
)
