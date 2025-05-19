import httpx

def test_get_problem():
    url = "http://127.0.0.1:8000/contests/abc405/problems/abc405_a"
    params = {"force_refresh": "true"}
    headers = {"accept": "application/json"}

    response = httpx.get(url, params=params, headers=headers)

    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    assert response.headers["content-type"].startswith("application/json")
    
    # Puedes agregar más verificaciones si conoces la estructura del JSON
    json_data = response.json()
    assert "problem_id" in json_data or "title" in json_data  # Ajusta según tu API
    assert "title" in json_data or "statement" in json_data  # Ajusta según tu API
    assert "content" in json_data or "samples" in json_data  # Ajusta según tu API
    assert "time_limit" in json_data or "memory_limit" in json_data  # Ajusta según tu API
    assert "last_updated" in json_data  # Ajusta según tu API
