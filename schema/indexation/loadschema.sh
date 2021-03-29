#!/bin/bash
#This is a convenient script for loading all the schemas
set -e

if [ $# -ne 3 ]
then
    echo "Usage ./loadSchema.sh $BASE_URL $DATA_PARTITION $TOKEN"
    exit -1
fi

BASE_URL=$1
DATA_PARTITION=$2
TOKEN=$3

echo "Loading Schemas on '$BASE_URL', for DataPartition '$DATA_PARTITION'"


schemaFiles=$(ls *.json)
for schemaFile in $schemaFiles 
do
    echo "loading $schemaFile: "
    schema=$(sed "s/DATA_PARTITION_TAG/${DATA_PARTITION}/" ${schemaFile})
    echo $schema | head -c 100
    echo "..."

    curl \
    --location \
    --request POST "$BASE_URL/api/storage/v2/schemas" \
    --header "Content-Type: application/json" \
    --header "data-partition-id: $DATA_PARTITION" \
    --header "Authorization: Bearer $TOKEN" \
    --data-raw "${schema}"

    echo ""
    echo "---"

done
echo "Done!"
