"""Test that type imports are working correctly."""

from types_def.data.entity import Entity, EntityUrl, UrlType

def test_imports():
    """Verify that types can be imported and used."""
    entity = Entity(
        primary_name="Test Entity",
        urls=[]
    )
    assert isinstance(entity, Entity)

    url = EntityUrl(
        url="https://example.com",
        url_type=UrlType.WEBSITE
    )
    assert isinstance(url, EntityUrl)
    assert url.url_type == UrlType.WEBSITE 