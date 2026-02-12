# Pinned to Bookworm so Chrome's system deps don't break
FROM python:3.11-slim-bookworm

WORKDIR /app

# System deps for Chrome, ChromeDriver, and psycopg2
RUN apt-get update && apt-get install -y \
    gnupg2 ca-certificates curl wget unzip \
    libpq-dev gcc xvfb \
    libnss3 libgconf-2-4 \
    libxi6 libxrandr2 libasound2 libatk1.0-0 \
    libpangocairo-1.0-0 libgtk-3-0 \
    fonts-liberation libappindicator3-1 xdg-utils

# Chrome stable
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list && \
    apt-get update && apt-get install -y google-chrome-stable

# Matching ChromeDriver from Chrome for Testing API
RUN apt-get install -yqq unzip && \
    CHROME_VERSION=$(google-chrome --version | grep -oP '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+') && \
    CHROMEDRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
    wget -O /tmp/chromedriver.zip "$CHROMEDRIVER_URL" && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /usr/local/bin/chromedriver-linux64 && \
    rm /tmp/chromedriver.zip

ENV CHROME_BIN="/usr/bin/google-chrome"
ENV CHROMEDRIVER_PATH="/usr/local/bin/chromedriver"

# Install Python deps first (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Gunicorn for production, flask dev server for local dev.
# Preload so the scheduler starts once in the master process.
CMD ["gunicorn", "web:create_app()", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "300", \
     "--preload"]
