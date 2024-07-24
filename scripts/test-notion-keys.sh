#! /bin/bash
set -o pipefail

pushd $(dirname ${0}) > /dev/null

echo "fetches Notion data to the $(dirname ${0}) folder"

NOTION_IDS="NOTION_FINANCIAL_DATABASE_ID \
    NOTION_WORKINGHOURS_DATABASE_ID \
    NOTION_CREW_DATABASE_ID \
    NOTION_ALLOCATIONS_DATABASE_ID"

for id in ${NOTION_IDS}; do
    echo "#"
    echo "Fetching ${id} data"
    curl -s -X POST 'https://api.notion.com/v1/databases/'"$(eval echo \$${id})"'/query' \
         -H 'Authorization: Bearer '"$NOTION_KEY"'' \
         -H "Notion-Version: 2022-06-28" | jq . > ./${id}.json
    
    head ./${id}.json

    case $id in
        *_FINANCIAL_*)
            echo "Reading finance data"
            cat ${id}.json | jq '
                .results[].properties.Month.title[0].plain_text,
                .results[].properties."external-cost".formula.number,
                .results[].properties."real-income".formula.number,
                .results[].properties."SEK start".number,
                .results[].properties."EUR start".number,
                .results[].properties."AB-Cost".number,
                .results[].properties."OY-Cost".number
                ' > ${id}.txt
            ;;
        *_WORKINGHOURS_*)
            echo "Reading workinghours data"
            cat ${id}.json | jq '
                .results[].properties.User.title[0].plain_text,
                .results[].properties.Daily.number,
                .results[].properties.Delta.number,
                .results[].properties.Start.rich_text[0].plain_text,
                .results[].properties.Stop.rich_text[0].plain_text
                ' > ${id}.txt 
            ;;
        *_CREW_*)
            echo "Reading crew data"
            cat ${id}.json | jq '
                .results[].properties.Person.people[0].name,
                .results[].properties.Role.select.name,
                .results[].properties.Currency.select.name,
                .results[].properties."Total Cost".number,
                .results[].properties."Consulting Hours".number
                ' > ./${id}.txt
            ;;
        *_ALLOCATIONS_*)
            echo "Reading allocations data"
            cat ${id}.json | jq -r '
                .results[].properties.Assign.people[].name
                ' > ./${id}.txt
            ;;
        *)
            echo -n "Error unknown database id"
            exit 1
            ;;
    esac
done

popd > /dev/null
