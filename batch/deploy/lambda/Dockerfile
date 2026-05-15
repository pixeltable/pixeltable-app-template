FROM public.ecr.aws/lambda/python:3.12

RUN dnf install -y gcc postgresql-devel && dnf clean all

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --python /var/lang/bin/python3.12
ENV UV_PROJECT_ENVIRONMENT=.venv

COPY schema.py pipeline.py sample_batch.json ./
COPY handler.py ./

CMD ["handler.lambda_handler"]
