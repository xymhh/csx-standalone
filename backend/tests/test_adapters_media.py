import httpx

from csx.adapters.media.emby import EmbyClient


def test_emby_probe_reads_system_info():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"ServerName": "Home", "Version": "4.8"})

    client = EmbyClient(
        "https://media.test/", "secret", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    info = client.probe()
    assert info.name == "Home"
    assert info.version == "4.8"
    assert seen[0].url.path == "/System/Info"
    assert seen[0].headers["X-Emby-Token"] == "secret"
    assert seen[0].url.params["api_key"] == "secret"


def test_jellyfin_refresh_supports_optional_library_id():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(204)

    client = EmbyClient(
        "https://media.test",
        "key",
        provider="jellyfin",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    client.refresh("library-1")
    assert seen[0].method == "POST"
    assert seen[0].url.path == "/Library/Refresh"
    assert seen[0].url.params["LibraryId"] == "library-1"


def test_server_probe_propagates_connection_failure():
    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    client = EmbyClient(
        "https://media.test", "", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    try:
        client.probe()
    except httpx.ConnectError as error:
        assert str(error) == "offline"
    else:
        raise AssertionError("expected connection failure")
