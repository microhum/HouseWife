FROM ubuntu:22.04

# Install Python and other dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    openjdk-17-jdk \
    && apt-get clean

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /app
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY --chown=user . /app

EXPOSE 2333
RUN chmod +x ./run.sh
CMD ["sh", "-c", "./run.sh"]