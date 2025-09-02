# Render-friendly Dockerfile: listens on $PORT
FROM mambaorg/micromamba:1.5.8

COPY environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && micromamba clean --all --yes

WORKDIR /app
COPY . /app

# Render sets $PORT dynamically; Streamlit must bind to it
ENV PORT=10000
EXPOSE 10000

CMD ["bash","-lc","streamlit run app_streamlit.py --server.address=0.0.0.0 --server.port=${PORT} --browser.gatherUsageStats=false"]
