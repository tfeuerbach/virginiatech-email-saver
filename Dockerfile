# Use an official lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for Chrome, ChromeDriver, and PostgreSQL
RUN apt-get update && apt-get install -y \
    gnupg2 ca-certificates curl wget unzip \
    libpq-dev gcc xvfb \
    libnss3 libgconf-2-4 \
    libxi6 libxrandr2 libasound2 libatk1.0-0 \
    libpangocairo-1.0-0 libgtk-3-0 \
    fonts-liberation libappindicator3-1 xdg-utils

# Install Chrome (latest stable)
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list && \
    apt-get update && apt-get install -y google-chrome-stable

# Fetch the correct ChromeDriver version from Chrome for Testing API
# Fetch the correct ChromeDriver version from Chrome for Testing API
RUN apt-get install -yqq unzip && \
    CHROME_VERSION=$(google-chrome --version | grep -oP '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+') && \
    CHROMEDRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
    wget -O /tmp/chromedriver.zip "$CHROMEDRIVER_URL" && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /usr/local/bin/chromedriver-linux64 && \
    rm /tmp/chromedriver.zip

# Set ChromeDriver and Chrome paths
ENV CHROME_BIN="/usr/bin/google-chrome"
ENV CHROMEDRIVER_PATH="/usr/local/bin/chromedriver"

# Copy only requirements first (to leverage Docker's caching)
COPY requirements.txt .

# Install Python dependencies, including Selenium
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .

# Expose Flask's default port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=web
ENV FLASK_ENV=production
ENV FLASK_RUN_HOST=0.0.0.0

# Run Flask app
CMD ["flask", "run"]
