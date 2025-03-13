import requests
import json
import os
import re
import fitz  # PyMuPDF
import argparse
import sys
import io
import yaml

PDF_URL = "https://ultra-portalstatic.ultradns.com/static/console/docs/REST-API_User_Guide.pdf"

def download_pdf_from_url(url):
    """Downloads the PDF from the specified URL and returns it as a bytes object."""
    try:
        print(f"Downloading PDF from {url}...")
        response = requests.get(url)
        response.raise_for_status()
        print("Download complete")
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF: {e}")
        return None

def find_table_pages(pdf_content, search_term="IP Probes by Region", start_page=1, end_page=None):
    """
    Search through the PDF to find pages that contain the specified search term.
    Returns a list of page numbers (1-indexed) that contain the search term.
    """
    try:
        # Open PDF from memory
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        if end_page is None:
            end_page = len(doc)
        else:
            end_page = min(end_page, len(doc))
        
        found_pages = []
        
        for page_num in range(start_page - 1, end_page):
            page = doc[page_num]
            text = page.get_text()
            
            if search_term.lower() in text.lower():
                found_pages.append(page_num + 1)  # Convert to 1-indexed
                print(f"Found '{search_term}' on page {page_num + 1}")
        
        doc.close()
        return found_pages
    except Exception as e:
        print(f"Error searching PDF: {e}")
        return []

def print_pdf_content(pdf_content, pages, verbose=False):
    """
    Debug function to print the raw text content of the specified pages
    to understand the structure of the PDF.
    """
    if not verbose:
        return
        
    try:
        # Parse page range if it's a string
        if isinstance(pages, str):
            page_range = pages.split("-")
            start_page = int(page_range[0]) - 1  # PyMuPDF uses 0-based indexing
            end_page = int(page_range[1]) - 1 if len(page_range) > 1 else start_page
            pages_to_print = range(start_page, end_page + 1)
        else:
            # If pages is a list, convert to 0-indexed
            pages_to_print = [p - 1 for p in pages]
        
        # Open PDF from memory
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        # Process each page in the range
        for page_num in pages_to_print:
            if page_num >= len(doc) or page_num < 0:
                print(f"Warning: Page {page_num + 1} does not exist in the PDF")
                continue
            
            print(f"\n--- PAGE {page_num + 1} CONTENT ---")
            page = doc[page_num]
            text = page.get_text()
            print(text)
            print(f"--- END OF PAGE {page_num + 1} CONTENT ---\n")
        
        # Close the document
        doc.close()
    except Exception as e:
        print(f"Error printing PDF content: {e}")

def normalize_region_name(region_name):
    """
    Normalize region names by replacing Unicode dashes with regular hyphens
    and performing other cleanup.
    """
    # Replace Unicode en-dash and em-dash with regular hyphen
    normalized = region_name.replace('\u2013', '-').replace('\u2014', '-')
    return normalized

def extract_ip_probes(pdf_content, pages):
    """
    Extracts the 'IP Probes by Region Available' table from the specified 
    PDF pages and returns a list of dictionaries with Region, IPv4, and IPv6.
    """
    try:
        # Parse page range if it's a string
        if isinstance(pages, str):
            page_range = pages.split("-")
            start_page = int(page_range[0]) - 1  # PyMuPDF uses 0-based indexing
            end_page = int(page_range[1]) - 1 if len(page_range) > 1 else start_page
            pages_to_process = range(start_page, end_page + 1)
        else:
            # If pages is a list, convert to 0-indexed
            pages_to_process = [p - 1 for p in pages]
        
        # Open PDF from memory
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        # Regular expressions for IPv4 and IPv6 addresses
        # More comprehensive IPv4 pattern
        ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        
        # Simpler IPv6 pattern that matches the specific format in this PDF
        simple_ipv6_pattern = r'2610:a1:[0-9a-fA-F]{4}:128::[0-9a-fA-F]{1,3}'
        
        # List of strings to exclude from region names
        exclude_from_regions = [
            "ip probes by region",
            "available",
            "2019",
            "ipv4",
            "ipv6",
            "region",
            "table",
            "page",
            "ultradns",
            "confidential"
        ]
        
        # List to store extracted data
        extracted_data = []
        current_region = None
        in_table_section = False
        
        # Process each page in the range
        for page_num in pages_to_process:
            if page_num >= len(doc) or page_num < 0:
                print(f"Warning: Page {page_num + 1} does not exist in the PDF")
                continue
            
            page = doc[page_num]
            text = page.get_text()
            
            # Check if we're in the table section
            if "ip probes by region" in text.lower():
                in_table_section = True
                print(f"Found IP Probes by Region table on page {page_num + 1}")
            
            if not in_table_section:
                continue
            
            # Split text into lines
            lines = text.split('\n')
            
            # Process each line
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip lines that are clearly not region names
                line_lower = line.lower()
                if any(exclude in line_lower for exclude in exclude_from_regions):
                    continue
                
                # Check if this line contains IP addresses
                ipv4_addresses = re.findall(ipv4_pattern, line)
                ipv6_addresses = re.findall(simple_ipv6_pattern, line)
                
                if ipv4_addresses or ipv6_addresses:
                    # This line contains IP addresses, so it's part of a region's data
                    if current_region:
                        # Normalize the region name
                        normalized_region = normalize_region_name(current_region)
                        
                        # Check if we already have an entry for this region
                        region_entry = next((item for item in extracted_data if item["region"] == normalized_region), None)
                        
                        if region_entry:
                            # Add to existing entry
                            region_entry["ipv4"].extend([ip for ip in ipv4_addresses if ip not in region_entry["ipv4"]])
                            region_entry["ipv6"].extend([ip for ip in ipv6_addresses if ip not in region_entry["ipv6"]])
                        else:
                            # Create new entry
                            extracted_data.append({
                                "region": normalized_region,
                                "ipv4": ipv4_addresses,
                                "ipv6": ipv6_addresses
                            })
                else:
                    # This line doesn't contain IP addresses, so it might be a region name
                    # Check if it's a reasonable length for a region name and doesn't start with a number
                    if len(line) > 1 and not line[0].isdigit() and not any(exclude in line_lower for exclude in exclude_from_regions):
                        current_region = line.strip()
        
        # Close the document
        doc.close()
        
        return extracted_data
    except Exception as e:
        print(f"Error extracting IP probes: {e}")
        return []

def save_to_file(data, output_file, format="json"):
    """Save the extracted data to a file in the specified format."""
    try:
        with open(output_file, 'w') as f:
            if format.lower() == "json":
                json.dump(data, f, indent=2)
            elif format.lower() == "yaml":
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            elif format.lower() == "csv":
                # Write CSV header
                f.write("Region,Type,IP Address\n")
                
                # Write data rows
                for region in data:
                    region_name = region["region"]
                    
                    # Write IPv4 addresses
                    for ip in region["ipv4"]:
                        f.write(f'"{region_name}",IPv4,{ip}\n')
                    
                    # Write IPv6 addresses
                    for ip in region["ipv6"]:
                        f.write(f'"{region_name}",IPv6,{ip}\n')
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        print(f"Data saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error saving data to file: {e}")
        return False

def output_data(data, format="json", output_file=None):
    """Output the data to a file or stdout in the specified format."""
    if output_file:
        return save_to_file(data, output_file, format)
    else:
        # Print to stdout
        if format.lower() == "json":
            print(json.dumps(data, indent=2))
        elif format.lower() == "yaml":
            print(yaml.dump(data, default_flow_style=False, sort_keys=False))
        elif format.lower() == "csv":
            # Write CSV header
            print("Region,Type,IP Address")
            
            # Write data rows
            for region in data:
                region_name = region["region"]
                
                # Write IPv4 addresses
                for ip in region["ipv4"]:
                    print(f'"{region_name}",IPv4,{ip}')
                
                # Write IPv6 addresses
                for ip in region["ipv6"]:
                    print(f'"{region_name}",IPv6,{ip}')
        else:
            print(f"Unsupported format: {format}")
            return False
        return True

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Extract UltraDNS SiteBacker Probe IPs from PDF")
    
    parser.add_argument("--url", default=PDF_URL,
                        help=f"URL to download the PDF from (default: {PDF_URL})")
    
    parser.add_argument("--output", "-o", default=None,
                        help="Output file path (if not specified, prints to stdout)")
    
    parser.add_argument("--format", "-f", choices=["json", "csv", "yaml"], default="json",
                        help="Output format (default: json)")
    
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print verbose output, including PDF content")
    
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Download PDF
    pdf_content = download_pdf_from_url(args.url)
    if not pdf_content:
        print("Failed to download PDF. Exiting.")
        sys.exit(1)
    
    # Find pages that might contain the table
    table_pages = find_table_pages(pdf_content, search_term="IP Probes by Region", start_page=1, end_page=300)
    
    if not table_pages:
        # Try alternative search terms
        table_pages = find_table_pages(pdf_content, search_term="Probes by Region", start_page=1, end_page=300)
    
    if not table_pages:
        # If still not found, try a broader search
        table_pages = find_table_pages(pdf_content, search_term="Probe", start_page=1, end_page=300)
        
    # If we found potential pages, print their content
    if table_pages:
        print(f"Found potential table pages: {table_pages}")
        print_pdf_content(pdf_content, table_pages, args.verbose)
        
        # Extract the table data from the found pages
        ip_probes_data = extract_ip_probes(pdf_content, table_pages)
    else:
        # If no pages found, try the original pages
        print("No table pages found. Trying original pages 202-203...")
        print_pdf_content(pdf_content, "202-203", args.verbose)
        ip_probes_data = extract_ip_probes(pdf_content, "202-203")

    # Output the data
    if ip_probes_data:
        output_data(ip_probes_data, args.format, args.output)
    else:
        print("No data extracted from the PDF.")
        sys.exit(1)

if __name__ == "__main__":
    main()
