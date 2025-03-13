# sitebacker_probe_ips

A Python tool to extract UltraDNS SiteBacker Probe IPs from the UltraDNS REST API User Guide PDF.

## Description

This tool downloads the UltraDNS REST API User Guide PDF and extracts the IP Probes by Region table, which contains the IPv4 and IPv6 addresses used by UltraDNS SiteBacker probes. This information is useful for configuring firewall rules to allow traffic from these probes.

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/sbarbett/sitebacker_probe_ips.git
   cd sitebacker_probe_ips
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package:
   ```
   pip install -e .
   ```

## Usage

Run the tool with default settings:
```
python -m sitebacker_probe_ips.main
```

This will:
1. Download the PDF from the UltraDNS website
2. Search for the IP Probes by Region table
3. Extract the IP addresses and regions
4. Print the data to stdout in JSON format

### Command-line Options

```
usage: main.py [-h] [--url URL] [--output OUTPUT] [--format {json,csv,yaml}] [--verbose]

Extract UltraDNS SiteBacker Probe IPs from PDF

options:
  -h, --help            show this help message and exit
  --url URL             URL to download the PDF from
  --output, -o OUTPUT   Output file path (if not specified, prints to stdout)
  --format, -f {json,csv,yaml}
                        Output format (default: json)
  --verbose, -v         Print verbose output, including PDF content
```

### Examples

Extract data and save as CSV:
```
python -m sitebacker_probe_ips.main --format csv --output sitebacker_probes.csv
```

Extract data and save as YAML:
```
python -m sitebacker_probe_ips.main --format yaml --output sitebacker_probes.yaml
```

Enable verbose output:
```
python -m sitebacker_probe_ips.main --verbose
```

## Output Format

### JSON (default)

The JSON output is an array of objects, each representing a region with its IPv4 and IPv6 addresses:

```json
[
  {
    "region": "North America - East",
    "ipv4": [
      "156.154.35.153",
      "156.154.35.154",
      ...
    ],
    "ipv6": [
      "2610:a1:3008:128::153",
      "2610:a1:3008:128::154",
      ...
    ]
  },
  ...
]
```

### YAML

The YAML output has the same structure as JSON but in YAML format:

```yaml
- region: North America - East
  ipv4:
  - 156.154.35.153
  - 156.154.35.154
  ...
  ipv6:
  - 2610:a1:3008:128::153
  - 2610:a1:3008:128::154
  ...
```

### CSV

The CSV output has three columns: Region, Type (IPv4 or IPv6), and IP Address:

```
Region,Type,IP Address
"North America - East",IPv4,156.154.35.153
"North America - East",IPv4,156.154.35.154
...
"North America - East",IPv6,2610:a1:3008:128::153
...
```

## Dependencies

- PyMuPDF (fitz): For PDF parsing
- requests: For downloading the PDF
- PyYAML: For YAML output format

## License

MIT 
