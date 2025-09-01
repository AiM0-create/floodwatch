
# Use mambaforge for fast conda installs
FROM mambaorg/micromamba:1.5.8 as base

# Create env
COPY environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml &&     micromamba clean --all --yes

# Set workdir
WORKDIR /app
COPY . /app

# Streamlit port
EXPOSE 8501

# Default command
CMD ["bash", "-lc", "streamlit run app_streamlit.py --server.port=8501 --server.address=0.0.0.0"]
