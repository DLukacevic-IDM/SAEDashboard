FROM python:3.11-slim 
 
WORKDIR /app

RUN apt update && apt install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# RUN curl -fsSL https://ollama.com/install.sh | sh

COPY ./requirements.txt /app/requirements.txt

# install requirements 
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# 
COPY . /app

# Make the entrypoint script executable
RUN chmod +x ./entrypoint.sh

# Expose the Ollama port
EXPOSE 11434

# Ensure ollama is in the PATH and tell it to listen on all network interfaces
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Set the entrypoint to the shell script
ENTRYPOINT ["./entrypoint.sh"]