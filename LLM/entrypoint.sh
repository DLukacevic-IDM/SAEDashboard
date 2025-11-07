#!/bin/bash
set -e

temp_model_file=/tmp/current_llm_model.txt 
[[ -f $temp_model_file ]] && rm $temp_model_file
#echo "Starting Ollama server in the background..."
#ollama serve > /dev/null 2>&1 &
#sleep 5  # Give the server a moment to start
#echo "Waiting for Ollama server to be ready..."
#timeout_seconds=120
#start_time=$(date +%s)
#while ! curl --silent --fail http://localhost:11434; do
#    elapsed_time=$(($(date +%s) - start_time))
#    if [ $elapsed_time -ge $timeout_seconds ]; then
#        echo "Timed out waiting for Ollama server. Check server logs for errors."
#        exit 1
#    fi
#    echo -n "."
#    sleep 5
#done
#echo "Ollama server is ready."

# ollama pull llama3.2:3b-instruct-q4_K_M 2>&1
# ollama pull phi4-mini:3.8b-q4_K_M 2>&1

# echo "Setting up vector database..."
# python3 workflow/vector_db.py

if [[ -s model/chroma_db/chroma.sqlite3 ]]; then
  echo "Chrome DB found!"
else
  echo "Error: Chrome DB NOT found!"
fi

uvicorn app:app --host 0.0.0.0 --port "5001"
