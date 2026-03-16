FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ca-certificates libgomp1 wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirement.txt ./requirement.txt

RUN pip install --upgrade pip \
    && pip install -r requirement.txt uwsgi

COPY . .

RUN chmod +x ./Docker/run.sh \
    && mkdir -p ./algos/models ./data ./temp \
    && if [ ! -f ./algos/models/deep_annotation_inference.h5 ]; then \
         wget -O ./algos/models/deep_annotation_inference.h5 \
           https://github.com/naurril/SUSTechPOINTS/releases/download/0.1/deep_annotation_inference.h5; \
       fi

VOLUME ["/app/data"]

EXPOSE 8092

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8092/', timeout=3)"

RUN echo "Builder Success 🎉 "

ENTRYPOINT ["./Docker/run.sh"]
