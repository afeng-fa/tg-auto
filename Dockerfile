FROM whyour/qinglong:latest

COPY main.py /app/main.py

CMD ["python", "main.py"]
