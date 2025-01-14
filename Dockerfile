FROM python:3.10.9

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY --chown=user . /app

RUN chmod +x run_lavalink.sh
ENTRYPOINT ["./run_lavalink.sh"]
CMD python3 src/main.py