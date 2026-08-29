import azure.functions as func
import json
import os

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

DOCUMENT_ID = os.environ["COSMOS_DOCUMENT_ID"]

@app.route(route="visitorcount", methods=["GET"])
def visitor_count(req: func.HttpRequest) -> func.HttpResponse:
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], credential=DefaultAzureCredential())
    container = client.get_database_client(os.environ["COSMOS_DATABASE_NAME"]) \
                       .get_container_client(os.environ["COSMOS_CONTAINER_NAME"])

    updated = container.patch_item(
        item=DOCUMENT_ID,
        partition_key=DOCUMENT_ID,
        patch_operations=[{"op": "incr", "path": "/total", "value": 1}],
    )

    return func.HttpResponse(
        body=json.dumps({"count": updated["total"]}),
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
    )
