"""Article extraction and text normalization service for NextGen NewsVerify.

Extracts news content, author, publisher, and publication dates from public URLs
using SSRF-safe retrieval and HTML sanitization. Also normalizes pasted text.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from security.url_validator import SafeUrlFetcher, is_safe_url
from security.input_validator import sanitize_html_content, validate_text_input


class ArticleExtractor:
    """Safe extractor for article text and metadata from URLs or pasted content."""

    def __init__(self, fetcher: Optional[SafeUrlFetcher] = None):
        self.fetcher = fetcher or SafeUrlFetcher()

    @staticmethod
    def normalize_pasted_text(text: str) -> str:
        """Normalize whitespace and control characters in pasted article text while preserving entities."""
        if not text:
            return ""
        # Remove null characters
        cleaned = text.replace("\x00", "")
        # Normalize newlines
        cleaned = re.sub(r"\r\n|\r", "\n", cleaned)
        # Normalize excessive paragraph breaks (more than 2 to 2)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        # Normalize excessive inline whitespace (tabs/spaces)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        return cleaned.strip()

    def extract_from_url(self, url: str) -> Dict[str, Any]:
        """Safely fetch and parse an article from a public URL."""
        is_safe, reason = is_safe_url(url)
        if not is_safe:
            raise ValueError(f"Unsafe URL rejected: {reason}")

        try:
            resp = self.fetcher.fetch(url)
        except Exception as e:
            raise ConnectionError(f"Failed to fetch article URL: {str(e)}")

        if resp.status_code != 200:
            raise ConnectionError(f"HTTP error {resp.status_code} while retrieving article.")

        # Decode HTML
        html_text = resp.text
        sanitized_html = sanitize_html_content(html_text)
        soup = BeautifulSoup(sanitized_html, "html.parser")

        # 1. Title Extraction
        title = None
        og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        # 2. Publisher Extraction
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower().lstrip("www.")
        publisher = None
        og_site = soup.find("meta", property="og:site_name") or soup.find("meta", attrs={"name": "publisher"})
        if og_site and og_site.get("content"):
            publisher = og_site["content"].strip()
        else:
            publisher = domain

        # 3. Publication Date Extraction
        pub_date = None
        date_meta = (
            soup.find("meta", property="article:published_time")
            or soup.find("meta", attrs={"name": "date"})
            or soup.find("meta", attrs={"name": "pubdate"})
            or soup.find("meta", attrs={"name": "publication_date"})
        )
        if date_meta and date_meta.get("content"):
            pub_date = date_meta["content"].strip()
        else:
            time_tag = soup.find("time")
            if time_tag:
                pub_date = time_tag.get("datetime") or time_tag.get_text(strip=True)

        # 4. Canonical URL
        canonical_url = None
        canon_tag = soup.find("link", rel="canonical")
        if canon_tag and canon_tag.get("href"):
            canonical_url = canon_tag["href"].strip()
        else:
            og_url = soup.find("meta", property="og:url")
            if og_url and og_url.get("content"):
                canonical_url = og_url["content"].strip()

        # 5. Author Extraction
        author = None
        author_meta = (
            soup.find("meta", attrs={"name": "author"})
            or soup.find("meta", property="article:author")
        )
        if author_meta and author_meta.get("content"):
            author = author_meta["content"].strip()

        # 6. Main Body Extraction
        # Look for <article>, <main>, or specific article body containers
        body_container = (
            soup.find("article")
            or soup.find("main")
            or soup.find(class_=re.compile(r"article-body|post-content|entry-content|story-content", re.I))
        )
        paragraphs = []
        if body_container:
            for p in body_container.find_all("p"):
                txt = p.get_text(strip=True)
                if len(txt) > 20:
                    paragraphs.append(txt)
        else:
            for p in soup.find_all("p"):
                txt = p.get_text(strip=True)
                if len(txt) > 25:
                    paragraphs.append(txt)

        article_text = "\n\n".join(paragraphs).strip()

        # If article_text is empty or too short, check fallback text
        if len(article_text) < 100:
            og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
            if og_desc and og_desc.get("content") and len(og_desc["content"]) > len(article_text):
                article_text = og_desc["content"].strip()

        is_valid, err, cleaned_text = validate_text_input(article_text, min_chars=30)
        if not is_valid:
            raise ValueError(f"Extracted content is too short or unusable ({err}). Please paste article text manually.")

        return {
            "title": title or "Untitled Article",
            "text": cleaned_text,
            "publisher": publisher,
            "domain": domain,
            "author": author,
            "publication_date": pub_date,
            "canonical_url": canonical_url or url,
            "is_https": url.lower().startswith("https://"),
            "url": url,
        }
