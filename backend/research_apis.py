"""
Research APIs module for academic paper search
Supports arXiv, PubMed, and other academic databases
"""

import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Dict
from datetime import datetime


def search_arxiv(query: str, max_results: int = 10) -> List[Dict]:
    """
    Search arXiv for academic papers

    Args:
        query: Search query
        max_results: Maximum number of results to return

    Returns:
        List of paper dictionaries with title, authors, abstract, url, etc.
    """
    try:
        # Build arXiv API query
        base_url = "http://export.arxiv.org/api/query?"
        params = {
            'search_query': query,
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }

        url = base_url + urllib.parse.urlencode(params)
        logging.info(f"arXiv search: {url}")

        # Fetch results
        with urllib.request.urlopen(url, timeout=10) as response:
            data = response.read()

        # Parse XML response
        root = ET.fromstring(data)

        # Extract namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom',
              'arxiv': 'http://arxiv.org/schemas/atom'}

        results = []

        for entry in root.findall('atom:entry', ns):
            try:
                # Extract basic info
                title = entry.find('atom:title', ns)
                title_text = title.text.strip().replace('\n', ' ') if title is not None else "No title"

                summary = entry.find('atom:summary', ns)
                summary_text = summary.text.strip().replace('\n', ' ')[:500] if summary is not None else "No abstract"

                # Get arXiv ID and URL
                id_elem = entry.find('atom:id', ns)
                arxiv_url = id_elem.text if id_elem is not None else ""

                # Extract arXiv ID from URL
                arxiv_id = arxiv_url.split('/')[-1] if arxiv_url else "unknown"

                # Get authors
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None:
                        authors.append(name.text)

                authors_str = ", ".join(authors) if authors else "Unknown authors"

                # Get publication date
                published = entry.find('atom:published', ns)
                pub_date = published.text[:10] if published is not None else "Unknown"

                # Get categories
                categories = []
                for category in entry.findall('atom:category', ns):
                    term = category.get('term')
                    if term:
                        categories.append(term)

                categories_str = ", ".join(categories[:3]) if categories else "N/A"

                # Get PDF link
                pdf_url = None
                for link in entry.findall('atom:link', ns):
                    if link.get('title') == 'pdf':
                        pdf_url = link.get('href')
                        break

                # Build result
                result = {
                    "title": title_text,
                    "authors": authors_str,
                    "abstract": summary_text,
                    "url": arxiv_url,
                    "pdf_url": pdf_url or arxiv_url.replace('/abs/', '/pdf/') + '.pdf',
                    "arxiv_id": arxiv_id,
                    "published": pub_date,
                    "categories": categories_str
                }

                results.append(result)

            except Exception as e:
                logging.error(f"Error parsing arXiv entry: {e}")
                continue

        logging.info(f"Found {len(results)} arXiv papers")
        return results

    except Exception as e:
        logging.error(f"arXiv search failed: {e}")
        return [{
            "title": "Search Error",
            "authors": "N/A",
            "abstract": f"Failed to search arXiv: {str(e)}",
            "url": "",
            "pdf_url": "",
            "arxiv_id": "error",
            "published": "N/A",
            "categories": "N/A"
        }]


def search_pubmed(query: str, max_results: int = 10) -> List[Dict]:
    """
    Search PubMed for biomedical papers
    Note: Requires NCBI API key for production use

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        List of paper dictionaries
    """
    try:
        # Build PubMed API query (E-utilities)
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            'db': 'pubmed',
            'term': query,
            'retmax': max_results,
            'retmode': 'json',
            'sort': 'relevance'
        }

        url = base_url + '?' + urllib.parse.urlencode(params)
        logging.info(f"PubMed search: {url}")

        # Fetch results
        with urllib.request.urlopen(url, timeout=10) as response:
            import json
            data = json.loads(response.read())

        # Extract PMIDs
        pmids = data.get('esearchresult', {}).get('idlist', [])

        if not pmids:
            return []

        # Fetch details for each PMID
        results = []
        for pmid in pmids[:max_results]:
            try:
                # Fetch summary
                summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"

                with urllib.request.urlopen(summary_url, timeout=5) as response:
                    summary_data = json.loads(response.read())

                paper = summary_data.get('result', {}).get(pmid, {})

                title = paper.get('title', 'No title')
                authors_list = paper.get('authors', [])
                authors = ', '.join([a.get('name', '') for a in authors_list[:3]])
                if len(authors_list) > 3:
                    authors += ' et al.'

                results.append({
                    "title": title,
                    "authors": authors or "Unknown authors",
                    "abstract": paper.get('abstract', 'No abstract available')[:500],
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "pmid": pmid,
                    "published": paper.get('pubdate', 'Unknown'),
                    "journal": paper.get('source', 'Unknown journal')
                })

            except Exception as e:
                logging.error(f"Error fetching PubMed {pmid}: {e}")
                continue

        return results

    except Exception as e:
        logging.error(f"PubMed search failed: {e}")
        return [{
            "title": "Search Error",
            "authors": "N/A",
            "abstract": f"Failed to search PubMed: {str(e)}",
            "url": "",
            "pmid": "error",
            "published": "N/A",
            "journal": "N/A"
        }]


def search_semantic_scholar(query: str, max_results: int = 10) -> List[Dict]:
    """
    Search Semantic Scholar for academic papers

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        List of paper dictionaries
    """
    try:
        import json

        base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': query,
            'limit': max_results,
            'fields': 'title,authors,abstract,year,url,citationCount,venue'
        }

        url = base_url + '?' + urllib.parse.urlencode(params)
        logging.info(f"Semantic Scholar search: {url}")

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        results = []
        for paper in data.get('data', []):
            authors = ', '.join([a.get('name', '') for a in paper.get('authors', [])[:3]])
            if len(paper.get('authors', [])) > 3:
                authors += ' et al.'

            results.append({
                "title": paper.get('title', 'No title'),
                "authors": authors or "Unknown authors",
                "abstract": (paper.get('abstract') or 'No abstract available')[:500],
                "url": paper.get('url', ''),
                "year": paper.get('year', 'Unknown'),
                "citations": paper.get('citationCount', 0),
                "venue": paper.get('venue', 'Unknown')
            })

        return results

    except Exception as e:
        logging.error(f"Semantic Scholar search failed: {e}")
        return [{
            "title": "Search Error",
            "authors": "N/A",
            "abstract": f"Failed to search Semantic Scholar: {str(e)}",
            "url": "",
            "year": "N/A",
            "citations": 0,
            "venue": "N/A"
        }]
