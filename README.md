# PDF Data Extractor with OpenAI

Automatically extract structured data from PDF documents using OpenAI's file analysis capabilities. This script processes PDFs through ChatGPT's API and outputs results in CSV format.

## Features

- 🔍 Direct PDF upload to OpenAI API (no manual text extraction)
- 📊 Structured JSON output converted to CSV
- ⚙️ Configurable data fields extraction
- 🔄 Automatic retries with exponential backoff
- 📝 Detailed error logging
- 🧹 Resource cleanup (deletes uploaded files after processing)

## Installation

1. Clone repository:
```bash
git clone https://github.com/kneeraazon404/json-from-pdf-to-csv
cd json-from-pdf-to-csv
```

2. Install dependencies:
```bash
pip install openai python-dotenv
```

3. Add your OpenAI API key to the `.env` file:
```env
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Place PDF files in the `pdfs/` directory
2. Run the script:
```bash
python json-from-pdf-to-csv.py
```
3. Find results in `extracted_data.csv`

## Configuration

Modify `FUNCTION_SCHEMA` in the script to change extracted fields:
```python
FUNCTION_SCHEMA = {
    # ... existing properties ...
    "properties": {
        "title": {"type": "string", "description": "Document title"},
        "author": {"type": "string", "description": "Document author"},
        "date": {"type": "string", "description": "Publication date"},
        # Add/remove fields as needed
    },
    "required": ["title", "author"]  # Required fields
}
```

## Sample Output

`extracted_data.csv`:
```csv
filename,title,author,date,keywords,summary,page_count,error
document1.pdf,"Climate Report","Jane Smith","2023-08-15","climate;environment","Analysis of climate patterns...",24,
document2.pdf,"Market Analysis","John Doe","2024-01-30","finance;economy","Global market trends...",32,
failed.pdf,,,,,,,"Processing timeout"
```

## Notes

- Requires GPT-4 Turbo or newer model
- Processing time varies by document size (avg 30-90 seconds/page)
- First 20 pages of each document are analyzed by default
- All uploaded files are automatically deleted after processing

## License

MIT License - see [LICENSE](LICENSE) for details
