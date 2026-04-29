"""
协议验证测试：使用真实 API key 调用 NewsAPI，确认返回的数据结构。
运行: pytest test_protocol/ -v -s
"""
import json
import httpx
import pytest


@pytest.mark.asyncio
async def test_newsapi_probe_queries():
    """探测哪些查询能返回结果，打印字段结构"""
    api_key = "158ae2fdfcd24dd68f8ab0ab40868e73"
    url = "https://newsapi.org/v2/everything"
    headers = {"X-Api-Key": api_key}

    # 测试多种查询组合
    queries = [
        {"q": "technology", "pageSize": 3, "language": "en"},
        {"q": "AI", "pageSize": 3, "language": "en"},
        {"q": "bitcoin", "pageSize": 3, "language": "en"},
        {"q": "人工智能", "pageSize": 3, "language": "zh"},
        {"q": "科技", "pageSize": 3, "language": "zh"},
    ]

    for params in queries:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params | {"sortBy": "publishedAt"}, headers=headers)
            data = resp.json()
            n = len(data.get("articles", []))
            print(f"q={params['q']:>10} lang={params['language']}: totalResults={data.get('totalResults', 0)} articles={n}")
            if n > 0:
                a = data["articles"][0]
                print(f"  → {a.get('title')[:60]}")
                print(f"    desc len={len(a.get('description','') or '')}  content len={len(a.get('content','') or '')}")
                # 打印第一个文章的完整结构供分析
                print(f"    FULL: {json.dumps(a, ensure_ascii=False)[:300]}")
                break  # 有一个成功就够了


@pytest.mark.asyncio
async def test_newsapi_article_structure():
    """确认文章字段结构"""
    api_key = "158ae2fdfcd24dd68f8ab0ab40868e73"
    headers = {"X-Api-Key": api_key}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://newsapi.org/v2/everything",
            params={"q": "人工智能", "pageSize": 1, "sortBy": "publishedAt", "language": "zh"},
            headers=headers,
        )
        data = resp.json()
        assert data["status"] == "ok"
        assert len(data["articles"]) > 0

        a = data["articles"][0]
        print("\n=== 完整文章结构 ===")
        print(json.dumps(a, indent=2, ensure_ascii=False))

        # 验证关键字段都存在
        assert "title" in a and a["title"]
        assert "url" in a and a["url"]
        assert "publishedAt" in a
        assert "description" in a
        assert "content" in a

        print(f"\n分析:")
        print(f"  source:  {a.get('source', {}).get('name', 'N/A')}")
        print(f"  author:  {a.get('author')}")
        print(f"  desc:    {(a.get('description') or '')[:120]}")
        print(f"  content: {(a.get('content') or '')[:120]}")
        print(f"  content is usable: {len((a.get('content') or '').strip()) > 50}")
