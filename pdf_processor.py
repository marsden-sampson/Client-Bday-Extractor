import pdfplumber
import fitz  # PyMuPDF
import io
import streamlit as st

class PDFProcessor:
    """Handles PDF text extraction using pdfplumber."""
    
    def __init__(self):
        self.supported_formats = ['.pdf']
    
    def extract_text(self, uploaded_file):
        """
        Extract text content from uploaded PDF file.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            str: Extracted text content
        """
        try:
            # Convert uploaded file to bytes
            pdf_bytes = uploaded_file.read()
            
            # Reset file pointer for potential reuse
            uploaded_file.seek(0)
            
            # Create BytesIO object for pdfplumber
            pdf_buffer = io.BytesIO(pdf_bytes)
            
            extracted_text = ""
            
            # Extract text from all pages
            with pdfplumber.open(pdf_buffer) as pdf:
                total_pages = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # Extract text from current page
                        page_text = page.extract_text()
                        
                        if page_text:
                            extracted_text += page_text + "\n\n"
                        
                        # Update progress for multi-page PDFs
                        if total_pages > 1:
                            progress = (page_num + 1) / total_pages
                            st.progress(progress, f"Processing page {page_num + 1} of {total_pages}")
                    
                    except Exception as e:
                        st.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                        continue
            
            return extracted_text.strip()
            
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def extract_tables(self, uploaded_file):
        """
        Extract table data from PDF if available.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            list: List of table data
        """
        try:
            pdf_bytes = uploaded_file.read()
            uploaded_file.seek(0)
            pdf_buffer = io.BytesIO(pdf_bytes)
            
            tables = []
            
            with pdfplumber.open(pdf_buffer) as pdf:
                for page in pdf.pages:
                    try:
                        page_tables = page.extract_tables()
                        if page_tables:
                            tables.extend(page_tables)
                    except Exception as e:
                        continue
            
            return tables
            
        except Exception as e:
            st.warning(f"Could not extract tables: {str(e)}")
            return []
    
    def get_pdf_info(self, uploaded_file):
        """
        Get basic information about the PDF.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            dict: PDF information
        """
        try:
            pdf_bytes = uploaded_file.read()
            uploaded_file.seek(0)
            pdf_buffer = io.BytesIO(pdf_bytes)
            
            with pdfplumber.open(pdf_buffer) as pdf:
                return {
                    'total_pages': len(pdf.pages),
                    'metadata': pdf.metadata or {},
                    'file_size': len(pdf_bytes)
                }
                
        except Exception as e:
            return {
                'total_pages': 0,
                'metadata': {},
                'file_size': 0,
                'error': str(e)
            }

    def extract_structured_data_with_coordinates(self, uploaded_file):
        """
        Extract structured data using the exact working PyMuPDF approach.
        Based on the proven ChatGPT solution.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            list: List of dictionaries with extracted client data
        """
        try:
            # Read the uploaded file into bytes
            file_bytes = uploaded_file.read()
            uploaded_file.seek(0)  # Reset for potential reuse
            
            # Open with PyMuPDF using the exact working approach
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
            import re
            
            # Regex to match header date format like "Wednesday - 1/1/2025"
            date_pattern = re.compile(r"([A-Za-z]+) - (\d{1,2})/(\d{1,2})/(\d{4})")
            status_order = {"Active": 1, "Dropout": 2, "NA": 3}
            
            data_rows = []
            current_date = None
            inside_birthday_list = True
            
            for page in doc:
                # Stop if we reach the Anniversary List section
                if "Anniversary List" in page.get_text():
                    break
            
                # Extract all words with position info
                words = page.get_text("words")  # (x0, y0, x1, y1, word, block, line, word_no)
                words = sorted(words, key=lambda w: (w[1], w[0]))  # Sort by Y then X
            
                # Group words by Y coordinate into "lines"
                line_buffer = {}
                y_tolerance = 2.0  # Tolerance for grouping same line
            
                for w in words:
                    x0, y0, x1, y1, word = w[:5]
                    y_key = None
                    for existing_y in line_buffer:
                        if abs(y0 - existing_y) <= y_tolerance:
                            y_key = existing_y
                            break
                    if y_key is None:
                        y_key = y0
                        line_buffer[y_key] = []
                    line_buffer[y_key].append((x0, word))
            
                for y in sorted(line_buffer.keys()):
                    line_words = sorted(line_buffer[y], key=lambda t: t[0])
                    line_text = " ".join([w[1] for w in line_words]).strip()
            
                    # Detect and set current date
                    date_match = date_pattern.match(line_text)
                    if date_match:
                        _, day, month, year = date_match.groups()
                        current_date = f"{year}-{int(month):02d}-{int(day):02d}"
                        continue
            
                    # Skip empty or header lines
                    if line_text in ["", "Client Name Status", "Birthday List"]:
                        continue
            
                    # Assume the largest X gap between words separates Name and Status
                    x_positions = [w[0] for w in line_words]
                    if len(x_positions) < 2:
                        continue  # can't separate columns
            
                    x_diffs = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
                    split_index = x_diffs.index(max(x_diffs)) + 1
            
                    name_words = [w[1] for w in line_words[:split_index]]
                    status_words = [w[1] for w in line_words[split_index:]]
            
                    name_text = " ".join(name_words).strip()
                    status_text = " ".join(status_words).strip()
            
                    # Only add if the status is valid
                    if status_text in status_order and current_date:
                        # Keep the full name and create short version
                        full_name = name_text.strip()
                        
                        # Create shortened name (First Name + Last Initial)
                        parts = full_name.split()
                        if len(parts) >= 2:
                            first_name = parts[0]
                            last_initial = parts[-1][0] if parts[-1] else ""
                            short_name = f"{first_name} {last_initial}"
                        else:
                            short_name = full_name
                        
                        data_rows.append({
                            'name': full_name,
                            'short_name': short_name,
                            'birthday': current_date,
                            'status': status_text,
                            'confidence': 'high',
                            'raw_line': line_text
                        })
            
            doc.close()
            
            st.success(f"Successfully extracted {len(data_rows)} client records!")
            return data_rows
            
        except Exception as e:
            st.error(f"Error extracting structured data from PDF: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return []
