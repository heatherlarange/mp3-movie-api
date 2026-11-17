# MP3 Movie API

This FastAPI application stores a movie collection in SQLite and serves it through a REST API. POST /upload accepts a CSV with the columns title, release_year, rating, and genre, and replaces the stored collection in a single transaction. src/database.py creates the connection and movies table, while MovieStorage performs all reads, filtering, sorting, and counting with SQL. GET /movies/search filters by minimum rating and returns only the requested columns. POST /movies/process loads the collection, runs the MP1 validation and cleaning pipeline from data_pipeline/, and saves the cleaned result back to SQLite. MovieCache caches GET /movies responses in FakeRedis. Every successful upload or processing run invalidates the cache, so clients never receive stale data.

## Running the API

```
python -m uvicorn main:app --reload
```

Then open http://127.0.0.1:8000/docs

## Running the tests

```
python -m pytest tests -v
```
## Sample request and output

send POST /movies/process after uploading fixtures/sample_movies.csv

```
{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {"enabled": true, "axis": "rows"},
    "outliers": {"enabled": true, "columns": ["rating"], "method": "iqr", "threshold": 1.5}
  }
}
```
Example Output:

```
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
```

```
23:24:10 INFO     main - Validated movies: rows 20 → 20
23:24:10 DEBUG    data_pipeline.data_processor - remove_duplicates: 20 -> 18 rows
23:24:10 DEBUG    data_pipeline.data_processor - handle_missing: 18 -> 18 rows
23:24:10 DEBUG    data_pipeline.data_processor - rating: method=iqr, threshold=1.5, lower=6.7, upper=9.099999999999998, removed=2
23:24:10 DEBUG    src.storage - Stored movies in SQLite: rows=16
23:24:10 DEBUG    src.cache - Invalidated movie cache
23:24:10 INFO     main - Processed movies: validation_removed=0, rows_before=20, rows_after=16
23:24:10 INFO     src.middleware - request_id=a711dcc7 POST /movies/process status=200 duration=15.3ms
INFO:     127.0.0.1:59219 - "POST /movies/process HTTP/1.1" 200 OK
```