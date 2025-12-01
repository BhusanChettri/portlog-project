"""Script to extract tariff data from PDF (run once, saves to disk)."""

import sys
from pathlib import Path

# Add src to path (scripts/ -> v0/ -> src/)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.data_extractor import TariffExtractor


def main():
    """Extract tariff data from PDF and save to disk."""
    print("=" * 60)
    print("Port Tariff Data Extraction")
    print("=" * 60)
    print()
    print("This will use LLM to extract structured tariff data from PDF.")
    print("The extracted data will be saved to disk for future use.")
    print()
    
    # Find PDF (relative to project root)
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    pdf_path = data_dir / "port-of-gothenburg-port-tariff-2025.pdf"
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return
    
    print(f"PDF found: {pdf_path}")
    print()
    
    # Output path (relative to project root)
    output_path = project_root / "extracted_data" / "tariff_rules.json"
    print(f"Output will be saved to: {output_path}")
    print()
    
    # Skip confirmation if running non-interactively
    import sys
    if sys.stdin.isatty():
        # Interactive mode - ask for confirmation
        response = input("Proceed with extraction? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Extraction cancelled.")
            return
        print()
    else:
        # Non-interactive mode - proceed automatically
        print("Proceeding with extraction (non-interactive mode)...")
        print()
    print("Starting extraction (this may take a few minutes)...")
    print()
    
    # Extract
    extractor = TariffExtractor()
    database = extractor.extract_from_pdf(pdf_path, output_path)
    
    print()
    print("=" * 60)
    print("Extraction Complete!")
    print("=" * 60)
    print(f"Total rules extracted: {len(database.rules)}")
    print(f"Saved to: {output_path}")
    print()
    print("You can now use TariffLoader.load_default() to load this data")
    print("without any LLM calls.")


if __name__ == "__main__":
    main()

