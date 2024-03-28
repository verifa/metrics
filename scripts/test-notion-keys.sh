#! /bin/sh

pushd $(dirname ${0}) > /dev/null

echo "fetches Notion data to the $(dirname ${0}) folder"

NOTION_IDS="NOTION_OKR_DATABASE_ID \
    NOTION_FINANCIAL_DATABASE_ID \
    NOTION_WORKINGHOURS_DATABASE_ID \
    NOTION_TASKS_DATABASE_ID \
    NOTION_CREW_DATABASE_ID \
    NOTION_ALLOCATIONS_DATABASE_ID"

for id in ${NOTION_IDS}; do
    curl -s -X POST 'https://api.notion.com/v1/databases/'"$(eval echo \$${id})"'/query' \
         -H 'Authorization: Bearer '"$NOTION_KEY"'' \
         -H "Notion-Version: 2022-06-28" | jq . > ${id}.json
done

popd > /dev/null
