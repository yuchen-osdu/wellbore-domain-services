FROM python:3.7-slim-buster

RUN apt-get update && apt-get install -y git
COPY requirements.txt requirements_dev.txt ./

RUN pip install -r requirements.txt
RUN pip install -r requirements_dev.txt

COPY ./app /app
ENV PYTHONPATH=./

# record some detail of the build, must be passed as --build-arg
ARG build_date
ARG build_number
ARG build_origin="Personal build"
ARG commit_id
ARG commit_branch
ENV OS_WELLBORE_DDMS_BUILD_DETAILS build_date=$build_date;build_number=$build_number;build_origin=$build_origin;commit_id=$commit_id;commit_branch=$commit_branch


EXPOSE 8097
WORKDIR ./

# Make the container run as non-root user
#(https://medium.com/better-programming/running-a-container-with-a-non-root-user-e35830d1f42a)
RUN addgroup --system appuser && adduser --system appuser && adduser appuser appuser
USER appuser

CMD ["uvicorn", "app.wdms_app:wdms_app", "--host", "0.0.0.0", "--port", "8097"]
