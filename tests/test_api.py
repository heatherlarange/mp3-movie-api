import pytest

from src import MovieStorage
import main

EXPECTED_COLUMNS = ["title", "release_year", "rating", "genre"]


def test_movies_persist(client, test_storage, uploaded_movies):
    other = MovieStorage(test_storage.db_path)

    df = other.get()
    assert other.count_movies() == 20
    assert len(df) == 20
    assert list(df.columns) == EXPECTED_COLUMNS

    original_titles = test_storage.get()["title"].tolist()
    assert df["title"].tolist() == original_titles

    db_ids = [row["id"] for row in other.select_columns(["title"], limit=100)]
    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200
    api_ids = [row["id"] for row in response.json()["data"]]

    assert db_ids == list(range(1, 21))
    assert api_ids == list(range(1, 21))


def test_cache_and_processing(client, uploaded_movies, processing_body):
    first_100 = client.get("/movies", params={"limit": 100})
    first_1 = client.get("/movies", params={"limit": 1})
    assert first_100.status_code == 200
    assert first_1.status_code == 200
    assert main.cache.get(100) == first_100.json()
    assert main.cache.get(1) == first_1.json()

    repeat = client.get("/movies", params={"limit": 100})
    assert repeat.status_code == 200
    assert repeat.json() == first_100.json()

    processed = client.post("/movies/process", json=processing_body)
    assert processed.status_code == 200
    body = processed.json()
    assert body["validation_rows_removed"] == 0
    assert body["cleaning_report"]["rows_before"] == 20
    assert body["cleaning_report"]["rows_after"] == 16
    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    after = client.get("/movies", params={"limit": 100})
    assert after.status_code == 200
    after_body = after.json()
    assert after_body["total_rows"] == 16

    titles = [row["title"] for row in after_body["data"]]
    assert titles == [f"Movie {chr(ord('A') + i)}" for i in range(16)]  # A..P

    ids = [row["id"] for row in after_body["data"]]
    assert ids == list(range(1, 17))

    assert main.cache.get(100) == after_body


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    first = client.get("/movies", params={"limit": 100})
    assert first.status_code == 200

    def fail(*args, **kwargs):
        pytest.fail("Database was called on a cache hit")

    monkeypatch.setattr(main.storage, "select_columns", fail)
    monkeypatch.setattr(main.storage, "count_movies", fail)

    second = client.get("/movies", params={"limit": 100})
    assert second.status_code == 200
    assert second.json() == first.json()
