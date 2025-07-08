import os
import json
import csv
import time
import logging
from pathlib import Path
from openai import OpenAI
from openai.types.beta.threads import Text, TextDelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

# Initialize OpenAI client with automatic retries
client = OpenAI(api_key=API_KEY, max_retries=3, timeout=30)

# Configuration
INPUT_DIR = Path("./pdfs")  # Folder containing PDF files
OUTPUT_CSV = "extracted_data.csv"  # Output CSV file name
FUNCTION_SCHEMA = {
    "name": "extract_data",
    "description": "Extract structured data from PDF documents",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Document title"},
            "author": {"type": "string", "description": "Document author"},
            "date": {"type": "string", "description": "Publication date (YYYY-MM-DD)"},
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key topics and keywords"
            },
            "summary": {"type": "string", "description": "Brief document summary"},
            "page_count": {"type": "integer", "description": "Number of pages"}
        },
        "required": ["title", "author", "summary"]
    }
}
PROMPT = """
Extract the following structured data from the PDF document:
- Title
- Author(s)
- Publication date
- Key keywords/topics
- Brief summary
- Page count

Return ONLY structured data using the extract_data function.
"""

# Setup logging
logging.basicConfig(
    filename="pdf_processing.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def create_assistant(client):
    """Create an assistant with retrieval and function calling capabilities"""
    return client.beta.assistants.create(
        name="PDF Data Extractor",
        instructions="You are an expert at extracting structured data from PDF documents.",
        tools=[
            {"type": "retrieval"},  # Required for file processing
            {"type": "function", "function": FUNCTION_SCHEMA}
        ],
        model="gpt-4-turbo",
    )

def process_pdf(pdf_path, assistant_id):
    """Process a single PDF file through OpenAI API"""
    try:
        # Upload PDF file
        with open(pdf_path, "rb") as f:
            file = client.files.create(file=f, purpose="assistants")
        logging.info(f"Uploaded: {pdf_path.name} (ID: {file.id})")

        # Create thread with file attachment
        thread = client.beta.threads.create(
            messages=[{
                "role": "user",
                "content": PROMPT,
                "file_ids": [file.id]
            }]
        )

        # Start processing
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )

        # Wait for completion with timeout
        start_time = time.time()
        while run.status not in ["completed", "failed", "cancelled", "expired"]:
            if time.time() - start_time > 300:  # 5-minute timeout
                raise TimeoutError("Processing timed out")
            
            time.sleep(5)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        # Handle failed runs
        if run.status != "completed":
            raise RuntimeError(f"Processing failed with status: {run.status}")
        
        # Get function call arguments
        messages = client.beta.threads.messages.list(thread.id)
        for message in messages.data:
            for tool_call in message.content:
                if (isinstance(tool_call, Text) and 
                    tool_call.text.value.startswith("{")):
                    return json.loads(tool_call.text.value)
        
        raise ValueError("No structured data found in response")
    
    except Exception as e:
        logging.error(f"Error processing {pdf_path.name}: {str(e)}")
        return {"error": str(e)}
    finally:
        # Clean up files
        if 'file' in locals():
            try:
                client.files.delete(file.id)
            except Exception as e:
                logging.warning(f"File deletion failed: {str(e)}")

def main():
    """Main processing workflow"""
    # Create assistant
    assistant = create_assistant(client)
    logging.info(f"Created assistant: {assistant.id}")

    # Prepare CSV output
    fieldnames = ["filename"] + list(FUNCTION_SCHEMA["parameters"]["properties"].keys()) + ["error"]
    csv_file = open(OUTPUT_CSV, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()

    # Process PDFs
    pdf_files = list(INPUT_DIR.glob("*.pdf"))
    if not pdf_files:
        logging.warning("No PDF files found in input directory")

    for pdf in pdf_files:
        logging.info(f"Processing: {pdf.name}")
        row = {"filename": pdf.name}
        
        try:
            # Process with 2 retries
            for attempt in range(3):
                try:
                    result = process_pdf(pdf, assistant.id)
                    if "error" in result:
                        raise RuntimeError(result["error"])
                    row.update(result)
                    row["error"] = ""
                    break
                except Exception as e:
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            row["error"] = str(e)
            logging.error(f"Final failure for {pdf.name}: {str(e)}")
        
        writer.writerow(row)
        csv_file.flush()  # Ensure data is written after each file

    # Clean up
    csv_file.close()
    client.beta.assistants.delete(assistant.id)
    logging.info("Processing completed. Assistant deleted.")

if __name__ == "__main__":
    main()
