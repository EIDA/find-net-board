FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /app
COPY . /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev
RUN pip install --no-cache-dir gunicorn
RUN python3 -m pip install --upgrade pip && python3 -m pip install --user pipx
ENV PATH=/root/.local/bin:$PATH
RUN pipx install poetry
RUN poetry config virtualenvs.create false && poetry install --no-dev
RUN python manage.py collectstatic --no-input
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "netstests.wsgi:application"]
