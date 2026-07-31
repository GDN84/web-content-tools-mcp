import os
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from fastmcp import FastMCP

mcp = FastMCP("web-content-tools")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WebContentTools/1.0)"
}

def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)

@mcp.tool()
def fetch_page(url: str, max_chars: int = 12000) -> dict:
    with httpx.Client(timeout=20, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
        response = client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    text = clean_text(response.text)[:max_chars]

    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(str(response.url), a["href"])
        if href not in seen:
            seen.add(href)
            links.append(href)

    return {
        "url": str(response.url),
        "title": title,
        "text": text,
        "links": links[:200],
    }

@mcp.tool()
def extract_metadata(url: str) -> dict:
    with httpx.Client(timeout=20, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
        response = client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    metadata = {}

    for tag in soup.find_all("meta"):
        key = tag.get("name") or tag.get("property")
        value = tag.get("content")
        if key and value and key not in metadata:
            metadata[key] = value

    return {
        "url": str(response.url),
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "metadata": metadata,
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
