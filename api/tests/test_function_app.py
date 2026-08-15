import json

import azure.functions as func

import function_app


def setup_function():
    function_app._cosmos_client = None
    function_app._cosmos_container = None


def test_visitor_count_options_returns_204_and_cors_headers():
    req = func.HttpRequest(
        method="OPTIONS",
        url="http://localhost:7071/api/visitorcount",
        params={},
        body=b"",
    )

    response = function_app.visitor_count(req)

    assert response.status_code == 204
    assert response.headers.get("Access-Control-Allow-Origin") == "*"


def test_visitor_count_get_increments_and_returns_total(mocker):
    get_config = mocker.patch("function_app._get_counter_configuration")
    get_container = mocker.patch("function_app._get_container")
    increment_counter = mocker.patch("function_app._increment_counter")

    get_config.return_value = {
        "document_id": "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
        "partition_key": "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
    }
    fake_container = object()
    get_container.return_value = fake_container
    increment_counter.return_value = 11

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
    assert payload["incremented"] is True
    increment_counter.assert_called_once_with(
        fake_container,
        "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
        "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
    )


def test_visitor_count_get_increment_false_reads_only(mocker):
    get_config = mocker.patch("function_app._get_counter_configuration")
    get_container = mocker.patch("function_app._get_container")
    read_counter = mocker.patch("function_app._read_counter")

    get_config.return_value = {
        "document_id": "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
        "partition_key": "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
    }
    fake_container = object()
    get_container.return_value = fake_container
    read_counter.return_value = 10

    req = func.HttpRequest(
        method="GET",
        url="http://localhost:7071/api/visitorcount?increment=false",
        params={"increment": "false"},
        body=b"",
    )

    response = function_app.visitor_count(req)
    payload = json.loads(response.get_body().decode("utf-8"))

    assert response.status_code == 200
    assert payload["count"] == 10
    assert payload["incremented"] is False
    read_counter.assert_called_once_with(
        fake_container,
        "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
        "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
    )


def test_webhook_post_increments(mocker):
    get_config = mocker.patch("function_app._get_counter_configuration")
    get_container = mocker.patch("function_app._get_container")
    increment_counter = mocker.patch("function_app._increment_counter")

    get_config.return_value = {
        "document_id": "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
        "partition_key": "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
    }
    fake_container = object()
    get_container.return_value = fake_container
    increment_counter.return_value = 12

    req = func.HttpRequest(
        method="POST",
        url="http://localhost:7071/api/visitorcount/webhook",
        params={},
        body=b"",
    )

    response = function_app.visitor_count_webhook(req)
    payload = json.loads(response.get_body().decode("utf-8"))

    assert response.status_code == 200
    assert payload["count"] == 12
    assert payload["incremented"] is True


def test_increment_counter_patches_total_field():
    class FakeContainer:
        def read_item(self, item, partition_key):
            return {"id": item, "total": 5}

        def patch_item(self, item, partition_key, patch_operations):
            expected = [{"op": "incr", "path": "/total", "value": 1}]
            if patch_operations != expected:
                raise AssertionError("Patch operation mismatch")
            return {"id": item, "total": 6}

    count = function_app._increment_counter(
        FakeContainer(),
        "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
        "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
    )

    assert count == 6


def test_read_counter_supports_total_field():
    class FakeContainer:
        def read_item(self, item, partition_key):
            return {"id": item, "total": 7}

    count = function_app._read_counter(
        FakeContainer(),
        "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
        "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
    )

    assert count == 7
