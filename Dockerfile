FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir streamlit pandas
COPY . .
CMD ["streamlit", "run", "validate_app.py", "--server.address=0.0.0.0"]