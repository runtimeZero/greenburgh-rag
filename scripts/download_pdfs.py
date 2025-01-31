import sys
import os
import json
import requests
import hashlib
from pathlib import Path
from datetime import datetime

# Add src directory to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_dir))

from utils.file_utils import load_json, save_json, get_discovered_urls_file

def download_pdf(url, output_dir):
    """
    Download PDF from URL if content-type is PDF.
    Returns (success, filename, error_message)
    """
    try:
        # Get headers first
        response = requests.head(url, allow_redirects=True)
        content_type = response.headers.get('content-type', '').lower()
        
        if 'application/pdf' not in content_type:
            return False, None, f"Not a PDF (content-type: {content_type})"
            
        # Download the PDF
        response = requests.get(url, stream=True)
        
        # Create filename from URL
        filename = hashlib.md5(url.encode()).hexdigest() + '.pdf'
        output_path = output_dir / filename
        
        # Save the PDF
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        return True, filename, None
        
    except Exception as e:
        return False, None, str(e)

def main():
    # Create output directory
    output_dir = Path('data/pdfs')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load discovered URLs
    urls_data = load_json(get_discovered_urls_file())
    if not urls_data or not urls_data.get('urls'):
        print("No URLs found in discovered_urls.json")
        return
        
    # Create log of PDF downloads
    pdf_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "pdfs_found": [],
        "errors": []
    }
    
    total_urls = len(urls_data['urls'])
    print(f"Processing {total_urls} URLs...")
    
    for i, url_data in enumerate(urls_data['urls'], 1):
        url = url_data['url']
        print(f"\nProcessing [{i}/{total_urls}]: {url}")
        
        success, filename, error = download_pdf(url, output_dir)
        
        if success:
            print(f"Downloaded PDF: {filename}")
            pdf_log['pdfs_found'].append({
                'url': url,
                'filename': filename,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            print(f"Error: {error}")
            pdf_log['errors'].append({
                'url': url,
                'error': error,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    # Save log
    log_file = output_dir / 'pdf_download_log.json'
    save_json(pdf_log, log_file)
    
    print(f"\nProcessing complete!")
    print(f"PDFs found: {len(pdf_log['pdfs_found'])}")
    print(f"Errors: {len(pdf_log['errors'])}")
    print(f"Log saved to: {log_file}")

if __name__ == "__main__":
    main() 