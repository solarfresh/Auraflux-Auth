##############################################################################
# Stage 1: Build the Cython extensions and install dependencies
##############################################################################
FROM python:3.14-slim AS builder

# RUN sed -i 's/deb.debian.org/debian.csie.ntu.edu.tw/g' /etc/apt/sources.list.d/debian.sources

# Set working directory
COPY api /api
COPY README.md /api

WORKDIR /api

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
RUN pip install --no-cache-dir pip -U && \
    pip install --no-cache-dir cython setuptools -U && \
    pip install --no-cache-dir -r requirements.txt
    # pip install --no-cache-dir git+https://github.com/solarfresh/auraflux-core.git@main#egg=auraflux-core

# Build the Cython extensions
RUN python setup.py build_ext --inplace

##############################################################################
# Stage 2: Create the final, smaller runtime image
##############################################################################
FROM python:3.14-slim AS runtime

# RUN sed -i 's/deb.debian.org/debian.csie.ntu.edu.tw/g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgraphviz-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire Python environment from the builder stage
# This includes the Python interpreter, site-packages, and compiled extensions.
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages

# Copy the Python binary and pip from the builder stage
COPY --from=builder /usr/bin /usr/bin
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the built files from the builder stage
COPY --from=builder /api /api

# Set working directory
WORKDIR /api

# Create necessary directories
RUN mkdir -p /auraflux/logs/

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE core.settings

# Expose the port the application will run on
EXPOSE 8000

# Run database migrations and start the Gunicorn server
CMD ["uvicorn", "core.asgi:application", "--host", "0.0.0.0", "--port", "8000"]