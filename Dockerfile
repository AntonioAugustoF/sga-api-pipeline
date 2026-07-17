FROM python:3.13-slim

# Logs aparecem imediatamente no `docker logs`, sem buffer
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências primeiro, em camada separada: só reinstala quando
# requirements.txt muda, não a cada alteração de código.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "orchestrators.serve"]
