FROM python:3.11-slim

RUN mkdir -p /code/app

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./alembic.ini /code/alembic.ini
COPY ./alembic /code/alembic

COPY main.py /code/app/main.py

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

