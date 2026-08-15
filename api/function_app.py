import azure.functions as func
import logging
import json
import os

from azure.cosmos import CosmosClient, exceptions as cosmos_exceptions
from azure.identity import DefaultAzureCredential

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

_cosmos_client = None
_cosmos_container = None


def _cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }


def _json_response(payload: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(payload),
        status_code=status_code,
        mimetype="application/json",
        headers=_cors_headers(),
    )


def _options_response() -> func.HttpResponse:
    return func.HttpResponse(status_code=204, headers=_cors_headers())


def _get_counter_configuration() -> dict[str, str]:
    endpoint = os.getenv(
        "COSMOS_ENDPOINT",
        f"https://{os.getenv('COSMOS_ACCOUNT_NAME', 'cloud-resume-nosql-db')}.documents.azure.com:443/",
    )
    database_name = os.getenv("COSMOS_DATABASE_NAME", "cloudresumedb")
    container_name = os.getenv("COSMOS_CONTAINER_NAME", "counter")

    if not endpoint:
        raise ValueError(
            "Missing required setting: COSMOS_ENDPOINT"
        )

    return {
        "endpoint": endpoint,
        "database_name": database_name,
        "container_name": container_name,
        "document_id": os.getenv("COSMOS_COUNTER_DOCUMENT_ID", "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb"),
        "partition_key": os.getenv(
            "COSMOS_COUNTER_PARTITION_KEY",
            os.getenv("COSMOS_COUNTER_DOCUMENT_ID", "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb"),
        ),
    }


def _get_container():
    global _cosmos_client
    global _cosmos_container

    if _cosmos_container is not None:
        return _cosmos_container

    config = _get_counter_configuration()
    key = os.getenv("COSMOS_KEY")

    if key:
        _cosmos_client = CosmosClient(config["endpoint"], credential=key)
    else:
        credential = DefaultAzureCredential()
        _cosmos_client = CosmosClient(config["endpoint"], credential=credential)

    db_client = _cosmos_client.get_database_client(config["database_name"])
    _cosmos_container = db_client.get_container_client(config["container_name"])
    return _cosmos_container


def _ensure_counter_document(container, document_id: str, partition_key: str) -> None:
    try:
        container.read_item(item=document_id, partition_key=partition_key)
    except cosmos_exceptions.CosmosResourceNotFoundError:
        container.create_item(
            body={
                "id": document_id,
                "total": 0,
            }
        )


def _increment_counter(container, document_id: str, partition_key: str) -> int:
    _ensure_counter_document(container, document_id, partition_key)
    updated = container.patch_item(
        item=document_id,
        partition_key=partition_key,
        patch_operations=[{"op": "incr", "path": "/total", "value": 1}],
    )
    return int(updated.get("total", 0))


def _read_counter(container, document_id: str, partition_key: str) -> int:
    _ensure_counter_document(container, document_id, partition_key)
    item = container.read_item(item=document_id, partition_key=partition_key)
    return int(item.get("total", item.get("count", 0)))

@app.route(route="visitorcount", methods=["GET", "OPTIONS"])
def visitor_count(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return _options_response()

    increment = req.params.get("increment", "true").lower() != "false"

    try:
        config = _get_counter_configuration()
        container = _get_container()

        if increment:
            count = _increment_counter(
                container,
                config["document_id"],
                config["partition_key"],
            )
        else:
            count = _read_counter(
                container,
                config["document_id"],
                config["partition_key"],
            )

        payload = {
            "count": count,
            "incremented": increment,
            "message": "Visitor counter updated" if increment else "Visitor counter read",
        }

        return _json_response(payload)
    except ValueError as exc:
        logging.exception("Configuration error while handling visitor counter request")
        return _json_response({"error": str(exc)}, status_code=500)
    except cosmos_exceptions.CosmosHttpResponseError:
        logging.exception("Cosmos DB error while handling visitor counter request")
        return _json_response(
            {"error": "Unable to access visitor counter in Cosmos DB"},
            status_code=500,
        )
    except Exception:
        logging.exception("Unexpected error while handling visitor counter request")
        return _json_response({"error": "Internal server error"}, status_code=500)


@app.route(route="visitorcount/webhook", methods=["POST", "OPTIONS"])
def visitor_count_webhook(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return _options_response()

    try:
        config = _get_counter_configuration()
        container = _get_container()
        count = _increment_counter(
            container,
            config["document_id"],
            config["partition_key"],
        )

        return _json_response(
            {
                "count": count,
                "incremented": True,
                "message": "Visitor counter updated via webhook",
            }
        )
    except ValueError:
        logging.exception("Configuration error while handling webhook request")
        return _json_response(
            {"error": "Missing required Cosmos configuration"},
            status_code=500,
        )
    except cosmos_exceptions.CosmosHttpResponseError:
        logging.exception("Cosmos DB error while handling webhook request")
        return _json_response(
            {"error": "Unable to access visitor counter in Cosmos DB"},
            status_code=500,
        )
    except Exception:
        logging.exception("Unexpected error while handling webhook request")
        return _json_response({"error": "Internal server error"}, status_code=500)
