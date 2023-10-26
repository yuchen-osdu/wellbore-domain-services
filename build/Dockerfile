# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM python:3.8-slim-bookworm

WORKDIR /
COPY requirements.txt ./

RUN pip install -r requirements.txt --no-cache-dir

COPY ./app /app
ENV PYTHONPATH=./

# record some detail of the build, must be passed as --build-arg
ARG build_date
ARG build_number
ARG build_origin="Personal build"
ARG commit_id
ARG commit_branch
ENV OS_WELLBORE_DDMS_BUILD_DETAILS build_date=$build_date;build_number=$build_number;build_origin=$build_origin;commit_id=$commit_id;commit_branch=$commit_branch


EXPOSE 8080
WORKDIR /

# Make the container run as non-root user
#(https://medium.com/better-programming/running-a-container-with-a-non-root-user-e35830d1f42a)
RUN addgroup --system appuser && adduser --system appuser && adduser appuser appuser

# Prevent CVE-2023-31484 by removing perl-base. To be removed, as soon as this CVE is fixed in official images
RUN apt-get purge perl-base -y --allow-remove-essential

USER appuser

CMD ["uvicorn", "app.base:base_app", "--host", "0.0.0.0", "--port", "8080"]
