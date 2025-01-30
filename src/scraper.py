import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import pdfplumber
import json
import time
from datetime import datetime
import io
import logging
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_same_domain(url: str, domain: str) -> bool:
    """Check if a URL belongs to the same domain."""
    parsed_url = urlparse(url)
    return parsed_url.netloc == domain

def get_domain(url: str) -> str:
    """Extract domain from a given URL."""
    return urlparse(url).netloc

def is_pdf_url(url: str) -> bool:
    """Check if URL likely points to a PDF"""
    pdf_patterns = [
        '/DocumentCenter/View/',  # Greenburgh document center pattern
        '.pdf',
        '/pdf/',
        'application/pdf'
    ]
    return any(pattern in url.lower() for pattern in pdf_patterns)

def extract_pdf_text(response: requests.Response) -> str:
    """Extract text from PDF content"""
    try:
        pdf_file = io.BytesIO(response.content)
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return ""

def get_page_metadata(url: str, resp: requests.Response) -> Dict:
    """Get page metadata including last modified date"""
    last_modified = resp.headers.get('last-modified')
    if last_modified:
        last_modified = datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z')
    else:
        last_modified = datetime.utcnow()
    
    return {
        "url": url,
        "last_modified": last_modified.isoformat(),
        "etag": resp.headers.get('etag'),
        "content_type": resp.headers.get('content-type'),
        "content_length": resp.headers.get('content-length'),
        "scraped_at": datetime.utcnow().isoformat()
    }

def discover_urls(start_url: str, max_depth: int) -> Dict:
    """
    Discover all URLs up to max_depth from start_url.
    Returns a dictionary of discovered URLs with metadata.
    """
    logger.info(f"Starting URL discovery from {start_url} with max_depth={max_depth}")
    domain = get_domain(start_url)
    discovered = {
        "metadata": {
            "start_url": start_url,
            "max_depth": max_depth,
            "domain": domain,
            "discovery_time": datetime.utcnow().isoformat()
        },
        "urls": []
    }
    
    queue = [(start_url, 0)]  # (url, depth)
    visited = set()

    while queue:
        current_url, depth = queue.pop(0)
        
        if depth > max_depth or current_url in visited:
            continue
            
        visited.add(current_url)
        logger.info(f"Discovering links from {current_url} (depth={depth})")
        
        try:
            time.sleep(1)  # Rate limiting
            resp = requests.get(current_url, timeout=10)
            if resp.status_code == 200:
                # Add to discovered URLs
                discovered["urls"].append({
                    "url": current_url,
                    "depth": depth,
                    "is_pdf": is_pdf_url(current_url),
                    "discovered_at": datetime.utcnow().isoformat()
                })
                
                # Only look for more links if it's an HTML page
                if 'text/html' in resp.headers.get('content-type', ''):
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    links = soup.find_all('a', href=True)
                    logger.info(f"Found {len(links)} links on {current_url}")
                    
                    for link in links:
                        abs_url = urljoin(current_url, link['href'])
                        if is_same_domain(abs_url, domain) and abs_url not in visited:
                            queue.append((abs_url, depth + 1))
                            
        except Exception as e:
            logger.error(f"Error discovering URLs from {current_url}: {e}")
    
    logger.info(f"URL discovery complete. Found {len(discovered['urls'])} URLs")
    return discovered

def scrape_single_url(url: str) -> Optional[Dict]:
    """
    Scrape content from a single URL.
    Returns a dictionary with the URL's content and metadata.
    """
    logger.info(f"Scraping content from {url}")
    
    try:
        time.sleep(1)  # Rate limiting
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"Failed to fetch URL: status code {resp.status_code}")
        
        # Determine content type and extract text
        if is_pdf_url(url):
            text_content = extract_pdf_text(resp)
            content_type = 'pdf'
        else:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Get main content area - first try modulecontent
            main_content = soup.find('div', id='modulecontent')
            if not main_content:
                # Fallback to contentarea if modulecontent not found
                main_content = soup.find('div', id='contentarea')
            
            # Get page title
            title = soup.find('h1') or soup.find('title')
            title = title.text.strip() if title else ''
            
            # Combine content meaningfully
            text_parts = []
            if title:
                text_parts.append(f"Title: {title}")
            
            if main_content:
                text_parts.append(main_content.get_text(separator=' ', strip=True))
            else:
                # Fallback to full page text if no main content found
                text_parts.append(soup.get_text(separator=' ', strip=True))
                
            text_content = "\n\n".join(text_parts)
            content_type = 'html'
            
        # Create and return page data
        page_data = {
            "url": url,
            "text": text_content,
            "type": content_type,
            "metadata": get_page_metadata(url, resp)
        }
        
        logger.info(f"Successfully scraped {url} ({len(text_content.split())} words)")
        return page_data
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return None

if __name__ == "__main__":
    # For testing
    import dotenv
    dotenv.load_dotenv()
    
    start_url = os.getenv("START_URL", "https://www.greenburghny.com/")
    max_depth = int(os.getenv("MAX_DEPTH", "1"))
    
    # Test URL discovery
    discovered = discover_urls(start_url, max_depth)
    print(f"Discovered {len(discovered['urls'])} URLs")
    
    # Test single URL scraping
    if discovered['urls']:
        test_url = discovered['urls'][0]['url']
        content = scrape_single_url(test_url)
        if content:
            print(f"Scraped {len(content['text'])} characters from {test_url}")