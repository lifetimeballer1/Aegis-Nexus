import json
import sqlite3
from datetime import timedelta
import news_feed_db as collector


def test_cache_miss_preserves_dated_evidence_without_relabeling_it(monkeypatch, tmp_path):
    now = collector.utc_now()
    article = {'url': 'https://example.org/report', 'title': 'Source report', 'source': 'Publisher',
               'published_date': (now-timedelta(hours=2)).isoformat(), 'sourceType': 'news',
               'summary_snippet': 'Original excerpt', 'credit': {'sourceId': 'publisher'}}
    stale = {**article, 'url': 'https://example.org/stale', 'published_date': (now-timedelta(days=collector.RETENTION_DAYS+1)).isoformat()}
    undated = {**article, 'url': 'https://example.org/undated', 'published_date': ''}
    future = {**article, 'url': 'https://example.org/future', 'published_date': (now+timedelta(days=1)).isoformat()}
    export = tmp_path/'live_articles.json'
    export.write_text(json.dumps({'articles': [article, stale, undated, future]}))
    monkeypatch.setattr(collector, 'JSON_PATH', export)
    with sqlite3.connect(':memory:') as conn:
        collector.init_db(conn)
        assert collector.restore_published_articles(conn) == 1
        recovered = json.loads(collector.export_json(conn))['articles'][0]
        for field in ('url', 'title', 'source', 'published_date', 'summary_snippet', 'credit'):
            assert recovered[field] == article[field]
        assert collector.restore_published_articles(conn) == 0


def test_invalid_export_fails_without_silently_discarding_evidence(monkeypatch, tmp_path):
    import pytest
    export = tmp_path/'live_articles.json'
    export.write_text('broken JSON')
    monkeypatch.setattr(collector, 'JSON_PATH', export)
    with sqlite3.connect(':memory:') as conn:
        collector.init_db(conn)
        with pytest.raises(json.JSONDecodeError):
            collector.restore_published_articles(conn)
