# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

ARG version=3.13
RUN apk add python-${version} --no-cache

COPY /app ./app
COPY --from=builder /wdms/venv ./venv
COPY provider/os-wellbore-ddms-aws/build-aws/osdu_api.ini .

RUN chown -R nonroot:nonroot /wdms/app

USER nonroot

ENTRYPOINT ["uvicorn"]
CMD ["app.wdms_app:wdms_app", "--host", "0.0.0.0", "--port", "8080"]