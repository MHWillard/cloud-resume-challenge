import json
import os
from pathlib import Path

import azure.functions as func
from dotenv import load_dotenv

import function_app

# Real resource names live in the gitignored .env file, not in source.
load_dotenv(Path(__file__).parent / ".env")


def test_visitor_count_increments_and_returns_total(mocker, monkeypatch):
    monkeypatch.setenv("COSMOS_ENDPOINT", os.environ["COSMOS_ENDPOINT"])
    monkeypatch.setenv("COSMOS_DATABASE_NAME", os.environ["COSMOS_DATABASE_NAME"])
    monkeypatch.setenv("COSMOS_CONTAINER_NAME", os.environ["COSMOS_CONTAINER_NAME"])

    mocker.patch("function_app.DefaultAzureCredential")

    fake_container = mocker.Mock()
    fake_container.patch_item.return_value = {"total": 11}

    fake_db_client = mocker.Mock()
    fake_db_client.get_container_client.return_value = fake_container

    fake_client = mocker.Mock()
    fake_client.get_database_client.return_value = fake_db_client

    mocker.patch("function_app.CosmosClient", return_value=fake_client)

    req = func.HttpRequest(
        method="GET",
        url="http://localhost:7071/api/visitorcount",
        params={},
        body=b"",
    )

    response = function_app.visitor_count(req)
    payload = json.loads(response.get_body().decode("utf-8"))

    assert response.status_code == 200
    assert payload["count"] == 11
    fake_container.patch_item.assert_called_once_with(
        item=function_app.DOCUMENT_ID,
        partition_key=function_app.DOCUMENT_ID,
        patch_operations=[{"op": "incr", "path": "/total", "value": 1}],
    )
