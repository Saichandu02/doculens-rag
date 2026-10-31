FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY scripts ./scripts
COPY data ./data
COPY ui ./ui
ENV DOCULENS_DATA_DIR=/srv/artifacts
EXPOSE 8100 8501
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
