FROM cgr.dev/chainguard/wolfi-base AS builder

ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/wdms/venv/bin:$PATH"

WORKDIR /wdms
ARG version=3.13
RUN apk add python-${version} py${version}-pip --no-cache

RUN python3 -m venv /wdms/venv

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --extra-index-url "https://community.opengroup.org/api/v4/projects/465/packages/pypi/simple"


FROM cgr.dev/chainguard/wolfi-base AS production

EXPOSE 8080
WORKDIR /wdms

ENV PYTHONUNBUFFERED=1
ENV PATH="/wdms/venv/bin:$PATH"

ARG build_date
ARG build_number
ARG build_origin="Personal build"
ARG commit_id
ARG commit_branch
ENV OS_WELLBORE_DDMS_BUILD_DETAILS=build_date=$build_date;build_number=$build_number;build_origin=$build_origin;commit_id=$commit_id;commit_branch=$commit_branch

ARG version=3.13
RUN apk add python-${version} --no-cache

COPY /app ./app
COPY --from=builder /wdms/venv ./venv

RUN chown -R nonroot:nonroot /wdms/app

USER nonroot

ENTRYPOINT ["uvicorn"]
CMD ["app.wdms_app:wdms_app", "--host", "0.0.0.0", "--port", "8080"]
