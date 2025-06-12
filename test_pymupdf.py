#!/usr/bin/env python3
import fitz
import streamlit as st

def test_pymupdf_methods():
    """Test PyMuPDF API methods to find the correct syntax."""
    try:
        # Create a test document
        doc = fitz.open()
        
        # Test with a real PDF if available
        print("PyMuPDF version:", fitz.version)
        print("Document created successfully")
        
        # Test available methods on a page object
        if len(doc) == 0:
            # Insert a test page
            page = doc.new_page()
            page.insert_text((100, 100), "Test text")
        else:
            page = doc[0]
            
        print("Available page methods with 'text':")
        for method in sorted(dir(page)):
            if 'text' in method.lower():
                print(f"  {method}")
                
        # Test the methods we need
        try:
            text = page.get_text()
            print(f"get_text() works: {len(text)} characters")
        except Exception as e:
            print(f"get_text() failed: {e}")
            
        try:
            words = page.get_text_words()
            print(f"get_text_words() works: {len(words)} words")
            if words:
                print(f"Sample word: {words[0]}")
        except Exception as e:
            print(f"get_text_words() failed: {e}")
            
        try:
            text_dict = page.get_text("dict")
            print(f"get_text('dict') works: {len(text_dict.get('blocks', []))} blocks")
        except Exception as e:
            print(f"get_text('dict') failed: {e}")
            
        doc.close()
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_pymupdf_methods()