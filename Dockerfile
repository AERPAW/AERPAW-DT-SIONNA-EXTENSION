# Pulling PyTorch base image for Sionna v2
FROM pytorch/pytorch:2.9.0-cuda13.0-cudnn9-runtime

# Set working directory
WORKDIR /app

# Ensuring Mitsuba/Optix environment
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics

# Install system dependencies required for Sionna RT and other packages
RUN apt-get update && apt-get install -y \
  build-essential \
  gcc \
  g++ \
  libgl1 \
  libglib2.0-0 \
  libgomp1 \
  iproute2 \
  iputils-ping \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python dependencies
# Removed --no-cache-dir for development
RUN pip install --upgrade pip && \
  pip install -r requirements.txt

# Copy application source code
COPY src/ ./src/

# Adding Scene Files
COPY data/scenes/lake-wheeler-scene.xml /app/scenes/
COPY data/scenes/meshes/lake-wheeler-building-roofs-output.ply /app/scenes/meshes/
COPY data/scenes/meshes/lake-wheeler-building-roofs-shaped-output.ply /app/scenes/meshes/
COPY data/scenes/meshes/lake-wheeler-building-walls-output.ply /app/scenes/meshes/
COPY data/scenes/meshes/terrain-mesh-small-output.ply /app/scenes/meshes/

# Setting environment variables for the containerized version
ENV PYTHONPATH=/app/src:$PYTHONPATH
ENV SCENE_PATH=/app/scenes/lake-wheeler-scene.xml

# Expose the fastAPI port for running it
EXPOSE 8000

# Set the working directory to src for running 
WORKDIR /app/src

# Binding to default port, then it will be recognized by the interface
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
