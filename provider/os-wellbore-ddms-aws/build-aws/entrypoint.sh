./ssl.sh;

if [ ${APPLICATION_PORT} -ne 443 ]
then
    uvicorn app.base:base_app --host 0.0.0.0 --port ${APPLICATION_PORT}
else
    uvicorn app.base:base_app --host 0.0.0.0 --port ${APPLICATION_PORT} --ssl-certfile ${SSL_CERT_PATH} --ssl-keyfile ${SSL_KEY_PATH}
fi