
import multiprocessing
import os

<<<<<<< HEAD
# Gunicorn Configuration for KAVACH-AI
=======
# Gunicorn Configuration for Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques
>>>>>>> 7df14d1 (UI enhanced)

# Bind to all interfaces
bind = "0.0.0.0:8000"

# Worker Setup
# Rule of thumb: 2-4 x $(NUM_CORES)
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
# AI processing can be slow, increase timeout
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process Naming
<<<<<<< HEAD
proc_name = "kavach_api"
=======
proc_name = "mmdds_api"
>>>>>>> 7df14d1 (UI enhanced)
