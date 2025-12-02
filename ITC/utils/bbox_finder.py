"""
Interactive Bounding Box Finder
Helps find exact coordinates for PDF text extraction

USAGE: 
    python -m ITC.utils.bbox_finder path/to/invoice.pdf
"""

import sys
import pdfplumber

from pathlib import Path

def find_text_coordinates(pdf_path):
    """
    Find and display all text with coordinates in a PDF
    Helps identify the exact bbox for date extraction
    """

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        return
    
    print("="*70)
    print("BBOX FINDER - Finding text coordinates in PDF")
    print("="*70)
    print()

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]

        print(f"Page dimensions: {page.width} x {page.height}")
        print()
        print(" Extracting all text elements...")
        print()

        # Get all words with their coordinates
        words = page.extract_words(
            x_tolerance=3,
            y_tolerance=3,
            keep_blank_chars=True
        )

        print("="*70)
        print("TEXT ELEMENTS (sorted top-to-bottom, left-to-right):")
        print("="*70)

        # Sory by position (top to bottom, left to right)
        words_sorted = sorted(words, key=lambda w: (w['top'], w['x0']))

        # Show first 30 elements (usually enough to find date at top)
        for i, word in enumerate(words_sorted[:30], 1):
            text = word['text']
            x0, y0, x1, y1 = word['x0'], word['top'], word['x1'], word['bottom']

            # Highlight if it looks like a date
            is_date = any(month in text for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
            
            marker = "Date?" if is_date else ""

            print(f"{i:2}. '{text}' {marker}")
            print(f"      Position: x0={x0:.1f}, y0={y0:.1f}, x1={x1:.1f}, y1={y1:.1f}")
            print()

        print("="*70)
        print("FINDING 'Bill date' or similar...")
        print("="*70)
        print()

        # Find elements that contain date-related keywords
        date_related = [w for w in words if any(kw in w['text'].lower() 
                                                  for kw in ['bill', 'date', 
                                                            'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                                                            'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])]
        
        if date_related:
            print("Found potential date elements:")
            for word in date_related[:10]:
                print(f"  - '{word['text']}' at x={word['x0']:.1f}, y={word['top']:.1f}")

            # Try to find the date value (usually follows "Bill date" label)
            print()
            print("="*70)
            print("SUGGESTED BOUNDING BOX:")
            print("="*70)

            # Find month names (likely the date we want)
            months = [w for w in date_related if any(m in w['text'] for m in
                        ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Oct', 'Nov', 'Dec'])]
            
            if months:
                # Get the month word and surrounding area
                month_word = months[0]
                x0 = month_word['x0'] - 5 # Start slightly before
                y0 = month_word['top'] - 2 # Start slightly above
                x1 = month_word['x1'] + 60 # Extend to cover 12, 2025
                y1 = month_word['bottom'] + 2 # Extend slightly below

                print(f"Based on date text '{month_word['text']}':")
                print(f"  'date_bbox': ({x0:.0f}, {y0:.0f}, {x1:.0f}, {y1:.0f})")
                print()
                print("📋 Copy this into your VENDOR_METADATA!")
                print()

                # Test the suggested bbbox
                print("=" * 70)
                print("TESTING SUGGESTED BBOX:")
                print("=" * 70)
                cropped = page.within_bbox((x0, y0, x1, y1))
                extracted = cropped.extract_text()
                print(f"Extracted text: '{extracted}'")
                print()
                
                if extracted:
                    print("✅ Success! This bbox captures text.")
                    print("   Make sure it's ONLY the date (e.g., 'Nov 12, 2025')")
                    print("   If it includes extra text, adjust the coordinates manually.")
                else:
                    print("⚠️  No text extracted. Try adjusting coordinates.")
        
        else:
            print("⚠️  Could not find date-related text automatically.")
            print("   Review the list above and identify the date manually.")

def test_custom_bbox(pdf_path):
    """
    Test a custom bounding box
    """
    print()
    print("=" * 70)
    print("CUSTOM BBOX TESTER")
    print("=" * 70)
    print()
    print("Enter coordinates to test (or press Enter to skip):")

    try:
        x0 = input("x0 (left edge): ").strip()
        if not x0:
            return
        
        y0 = input("y0 (top edge): ").strip()
        x1 = input("x1 (right edge): ").strip()
        y1 = input("y1 (bottom edge): ").strip()
        
        bbox = (float(x0), float(y0), float(x1), float(y1))
        
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            cropped = page.within_bbox(bbox)
            text = cropped.extract_text()
            
            print()
            print(f"Testing bbox: {bbox}")
            print(f"Extracted text: '{text}'")
            
            if text and text.strip():
                print("✅ Text found!")
            else:
                print("❌ No text found in this bbox")
    
    except ValueError:
        print("Invalid coordinates. Please enter numbers")
    except Exception as e:
        print(f" Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m ITC.utils.bbox_finder path/to/invoice.pdf")
        print()
        print("Example:")
        print("   python -m ITC.utils.bbox_finder ITC/invoices/ROGE04_3509_2-Dec-2025_68050-YYT-11-410.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Find coordinates automatically
    find_text_coordinates(pdf_path)

    #Optionally test custom coordinates
    test_custom_bbox(pdf_path)
            