from app.llm.llm_routing import llm_routing


def test_llm_routing_rows():
    data = llm_routing()
    assert len(data["rows"]) == 2
    roles = {r["role"] for r in data["rows"]}
    assert roles == {"Daily", "Strong"}
    for row in data["rows"]:
        assert row["model"]
        assert "price_in" in row and "price_out" in row
