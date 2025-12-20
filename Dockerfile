FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y bash && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x media_cleanup.sh enhanced_cleanup_v2.sh

EXPOSE 5000

ENV FLASK_APP=web_gui.py

CMD ["python", "web_gui.py"]
