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


FROM public.ecr.aws/docker/library/python:3.13-alpine3.22 as build


ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.python/bin:${PATH}"

RUN mkdir app
RUN apk update && apk upgrade

RUN apk add gcc musl-dev linux-headers libexpat perl python3-dev g++ bash build-base cmake jemalloc-dev boost-dev autoconf zlib-dev flex bison git tzdata lz4-dev
RUN apk add py3-pip py3-pyarrow py3-numpy py3-six cython py3-pytest py3-cffi py3-cffi-pyc xz-libs

RUN python3 -m venv "/app/.python/" --system-site-packages

COPY requirements.txt ./

RUN pip install --upgrade setuptools~=78.1.1 pip~=24.2
RUN pip install -r requirements.txt --no-cache-dir --extra-index-url "https://community.opengroup.org/api/v4/projects/465/packages/pypi/simple"


COPY ./app /app
ENV PYTHONPATH=./

FROM public.ecr.aws/docker/library/python:3.13-alpine3.22 as service

RUN apk update && apk upgrade

COPY --from=build /app /app

RUN apk add bash autoconf flex bison tzdata lz4
RUN apk add py3-pip py3-pyarrow py3-numpy py3-six cython py3-pytest py3-cffi py3-cffi-pyc

LABEL version="1.0"
LABEL maintainer="aws"

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.python/bin:${PATH}"

COPY provider/os-wellbore-ddms-aws/build-aws/osdu_api.ini .
ENV PYTHONPATH=./


EXPOSE ${APPLICATION_PORT}
WORKDIR ./

RUN addgroup -S -g 10001 appgroup \
 && adduser -S -H -u 10001 -G appgroup appuser

USER 10001:10001
CMD ["sh", "-c", "uvicorn app.wdms_app:wdms_app --host 0.0.0.0 --port ${APPLICATION_PORT:-8080}"]