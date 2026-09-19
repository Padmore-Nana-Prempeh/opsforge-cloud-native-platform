FROM python:3.13-slim

WORKDIR /opt/opsforge

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt 

COPY app ./app

EXPOSE 8001

CMD ["uvicorn", "app.inventory.main:app", "--host", "0.0.0.0", "--port", "8001"]
