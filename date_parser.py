import re
from datetime import datetime
from dateutil import parser as date_parser
import pandas as pd

class DateParser:
    """Handles extraction and parsing of birthday data from text."""
    
    def __init__(self):
        # Common date patterns
        self.date_patterns = [
            # MM/DD/YYYY, MM-DD-YYYY, MM.DD.YYYY
            r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b',
            # MM/DD/YY, MM-DD-YY, MM.DD.YY
            r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2})\b',
            # Month DD, YYYY
            r'\b([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})\b',
            # DD Month YYYY
            r'\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b',
            # YYYY-MM-DD (ISO format)
            r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b'
        ]
        
        # Common name patterns
        self.name_patterns = [
            # First Last
            r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b',
            # Last, First
            r'\b([A-Z][a-z]+),\s*([A-Z][a-z]+)\b',
            # First Middle Last
            r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\s+([A-Z][a-z]+)\b'
        ]
        
        # Month name mappings
        self.month_names = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2,
            'march': 3, 'mar': 3, 'april': 4, 'apr': 4,
            'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
            'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
    
    def extract_birthday_data(self, text):
        """
        Extract birthday data from text content.
        
        Args:
            text (str): Raw text content from PDF
            
        Returns:
            list: List of dictionaries containing name and birthday data
        """
        birthday_data = []
        
        # Split text into lines for processing
        lines = text.split('\n')
        
        # Process the document structure: date headers followed by client tables
        birthday_data = self._extract_structured_birthday_data(lines)
        
        # If no structured data found, fall back to line-by-line processing
        if not birthday_data:
            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Try to extract birthday information from each line
                extracted_data = self._extract_from_line(line, line_num)
                if extracted_data:
                    birthday_data.extend(extracted_data)
        
        # Remove duplicates based on name similarity
        birthday_data = self._remove_duplicates(birthday_data)
        
        return birthday_data
    
    def _extract_from_line(self, line, line_num):
        """Extract birthday data from a single line."""
        extracted_data = []
        
        # Find all dates in the line
        dates = self._find_dates_in_text(line)
        
        # Find all names in the line
        names = self._find_names_in_text(line)
        
        # Match names with dates
        if dates and names:
            # If we have equal numbers of names and dates, pair them
            if len(names) == len(dates):
                for name, date in zip(names, dates):
                    extracted_data.append({
                        'name': name,
                        'birthday': date,
                        'raw_line': line,
                        'line_number': line_num + 1,
                        'confidence': 'high'
                    })
            else:
                # Take the first name and first date
                extracted_data.append({
                    'name': names[0],
                    'birthday': dates[0],
                    'raw_line': line,
                    'line_number': line_num + 1,
                    'confidence': 'medium'
                })
        elif names and not dates:
            # Name without date - might be in adjacent lines
            for name in names:
                extracted_data.append({
                    'name': name,
                    'birthday': None,
                    'raw_line': line,
                    'line_number': line_num + 1,
                    'confidence': 'low'
                })
        
        return extracted_data
    
    def _find_dates_in_text(self, text):
        """Find all dates in a text string."""
        dates = []
        
        for pattern in self.date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    date_str = match.group(0)
                    parsed_date = self._parse_date_string(date_str)
                    if parsed_date:
                        dates.append(parsed_date)
                except:
                    continue
        
        return list(set(dates))  # Remove duplicates
    
    def _find_names_in_text(self, text):
        """Find all potential names in a text string."""
        names = []
        
        for pattern in self.name_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    if ',' in match.group(0):
                        # Last, First format
                        parts = match.group(0).split(',')
                        name = f"{parts[1].strip()} {parts[0].strip()}"
                    else:
                        name = match.group(0).strip()
                    
                    # Basic validation - avoid common false positives
                    if self._is_valid_name(name):
                        names.append(name)
                except:
                    continue
        
        return list(set(names))  # Remove duplicates
    
    def _parse_date_string(self, date_str):
        """Parse a date string into a standardized format."""
        try:
            # Try using dateutil parser first
            parsed_date = date_parser.parse(date_str, fuzzy=True)
            
            # Validate the date is reasonable for a birthday
            current_year = datetime.now().year
            if 1900 <= parsed_date.year <= current_year:
                return parsed_date.strftime('%Y-%m-%d')
            
        except:
            pass
        
        # Try manual parsing for specific patterns
        try:
            # Handle MM/DD/YY format (assuming 20xx for years < 50, 19xx for >= 50)
            if re.match(r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2}$', date_str):
                parts = re.split(r'[\/\-\.]', date_str)
                year = int(parts[2])
                if year < 50:
                    year += 2000
                else:
                    year += 1900
                
                month, day = int(parts[0]), int(parts[1])
                parsed_date = datetime(year, month, day)
                return parsed_date.strftime('%Y-%m-%d')
                
        except:
            pass
        
        return None
    
    def _is_valid_name(self, name):
        """Validate if a string is likely a person's name."""
        # Basic checks to avoid false positives
        words = name.split()
        
        # Should have 2-3 words
        if len(words) < 2 or len(words) > 3:
            return False
        
        # Each word should be capitalized and contain only letters
        for word in words:
            if not word.isalpha() or not word[0].isupper():
                return False
            if len(word) < 2:  # Very short names are suspicious
                return False
        
        # Avoid common false positives
        false_positives = {
            'Date Born', 'Birth Date', 'Client Name', 'Full Name',
            'First Last', 'Name Date', 'Page Number', 'Date Time'
        }
        
        if name in false_positives:
            return False
        
        return True
    
    def _extract_structured_data(self, text):
        """Extract data from structured formats like tables."""
        structured_data = []
        
        # Look for table-like structures
        lines = text.split('\n')
        
        # Check for common table headers
        header_indicators = ['name', 'birthday', 'birth', 'date', 'client']
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # If line contains header indicators, check following lines
            if any(indicator in line_lower for indicator in header_indicators):
                # Check next few lines for data
                for j in range(i + 1, min(i + 10, len(lines))):
                    data_line = lines[j].strip()
                    if data_line:
                        extracted = self._extract_from_line(data_line, j)
                        structured_data.extend(extracted)
        
        return structured_data
    
    def _extract_structured_birthday_data(self, lines):
        """Extract birthday data from simple 3-column format: Name | Date | Status."""
        birthday_data = []
        debug_info = {
            'total_lines': len(lines),
            'header_found': False,
            'clients_extracted': 0,
            'sample_lines': [],
            'skipped_lines': [],
        }
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Store sample lines for debugging
            if len(debug_info['sample_lines']) < 20:
                debug_info['sample_lines'].append(f"Line {i}: {line}")
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip header line
            if 'name' in line.lower() and 'date' in line.lower() and 'status' in line.lower():
                debug_info['header_found'] = True
                continue
            
            # Try to extract client data from 3-column format
            client_data = self._extract_from_three_column_format(line)
            if client_data:
                client_data['raw_line'] = line
                client_data['line_number'] = i
                birthday_data.append(client_data)
                debug_info['clients_extracted'] += 1
            else:
                # Track lines that might contain clients but weren't extracted
                if any(c.isalpha() for c in line) and len(line) > 5:
                    if len(debug_info['skipped_lines']) < 10:
                        debug_info['skipped_lines'].append(line)
        
        # Simple validation - all clients should already have proper birthdays from extraction
        
        # Store debug info for inspection
        self._debug_info = debug_info
        return birthday_data
    
    def _extract_date_header(self, line):
        """Extract date from header line like 'Wednesday - 1/1/2025'."""
        # Look for patterns like "Day - MM/DD/YYYY" or just "MM/DD/YYYY"
        date_patterns = [
            # Special leap year case: "Leap Year - 29/2/2025"
            r'Leap\s+Year\s*[-–]\s*(\d{1,2}/\d{1,2}/\d{4})',
            # Day name with dash and date
            r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*[-–]\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*[-–]\s*(\d{1,2}-\d{1,2}-\d{4})',
            r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*[-–]\s*(\d{1,2}\.\d{1,2}\.\d{4})',
            # Standalone dates
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{1,2}-\d{1,2}-\d{4})',
            r'(\d{1,2}\.\d{1,2}\.\d{4})',
            # Month names
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})',
            r'(\d{1,2})\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})',
        ]
        
        for i, pattern in enumerate(date_patterns):
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                if i < 6:  # Simple date patterns
                    date_str = match.group(1)
                else:  # Month name patterns
                    month_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)', line, re.IGNORECASE)
                    if month_match:
                        if i == 6:  # Month DD, YYYY
                            month_name = month_match.group(1)
                            day = match.group(1)
                            year = match.group(2)
                            date_str = f"{month_name} {day}, {year}"
                        else:  # DD Month YYYY
                            month_name = month_match.group(1)
                            day = match.group(1)
                            year = match.group(2)
                            date_str = f"{month_name} {day}, {year}"
                    else:
                        continue
                
                parsed_date = self._parse_date_string(date_str)
                if parsed_date:
                    return parsed_date
        
        return None
    
    def _is_table_header(self, line):
        """Check if line contains table headers like 'Client Name' and 'Status'."""
        line_lower = line.lower()
        return ('client name' in line_lower and 'status' in line_lower) or \
               ('name' in line_lower and 'status' in line_lower)
    
    def _extract_client_from_table_row(self, line, birthday):
        """Extract client name and status from a table row."""
        # Skip lines that are obviously not client data
        line_lower = line.lower().strip()
        skip_patterns = [
            'client name', 'status', 'page', 'total', 'summary', 'leap year'
        ]
        
        # Skip if line is just a header or empty
        if not line_lower or line_lower in skip_patterns:
            return None
        
        # Skip if line is just a status word alone
        if line_lower in ['active', 'dropout', 'na', 'inactive']:
            return None
        
        # Look for "First Name + Last Name" pattern with status
        # Pattern: "FirstName LastName" followed by "Active" or "Dropout"
        pattern_match = re.match(r'^([A-Za-z][a-z\'-]*)[\s]+([A-Za-z][a-z\'-]*)[\s]+(Active|Dropout|NA|Inactive)$', line.strip(), re.IGNORECASE)
        if pattern_match:
            first_name = pattern_match.group(1).strip()
            last_name = pattern_match.group(2).strip()
            status = pattern_match.group(3).strip()
            
            name = f"{first_name} {last_name}"
            return {
                'name': name,
                'birthday': birthday,
                'status': status,
                'raw_line': line,
                'confidence': 'high'
            }
        
        # Split by common delimiters to separate name and status
        parts = []
        
        # Try different splitting methods for table data
        if '\t' in line:  # Tab-separated
            parts = [p.strip() for p in line.split('\t') if p.strip()]
        elif '  ' in line:  # Multiple spaces (common in table layouts)
            parts = [p.strip() for p in re.split(r'\s{2,}', line) if p.strip()]
        else:
            # For the specific table format shown in screenshot
            # Look for pattern: "FirstName LastName" followed by "Status"
            words = line.split()
            if len(words) >= 3:
                # Try to identify where the name ends and status begins
                # Common status words that indicate the boundary
                status_keywords = ['active', 'dropout', 'na', 'inactive']
                
                # Find status keyword position
                status_idx = None
                for i, word in enumerate(words):
                    if word.lower() in status_keywords:
                        status_idx = i
                        break
                
                if status_idx is not None and status_idx >= 2:
                    # Found status, everything before it is the name
                    name_parts = words[:status_idx]
                    status_parts = words[status_idx:]
                    parts = [' '.join(name_parts), ' '.join(status_parts)]
                elif len(words) >= 3:
                    # Assume last word is status, rest is name
                    last_word = words[-1].lower()
                    if last_word in status_keywords:
                        parts = [' '.join(words[:-1]), words[-1]]
                    else:
                        # If last word doesn't look like status, try different split
                        # For "FirstName LastName Status" pattern
                        if len(words) == 3:
                            parts = [f"{words[0]} {words[1]}", words[2]]
                        else:
                            # More than 3 words, assume last is status
                            parts = [' '.join(words[:-1]), words[-1]]
            elif len(words) == 2:
                # Could be "Name Status" or "FirstName LastName"
                if words[1].lower() in ['active', 'dropout', 'na', 'inactive']:
                    parts = [words[0], words[1]]
                else:
                    # Assume both are name parts
                    parts = [' '.join(words), 'Unknown']
            else:
                # Single word or empty
                if len(words) == 1:
                    parts = [words[0], 'Unknown']
        
        # Clean and validate the extracted data
        if len(parts) >= 2:
            name = parts[0].strip()
            status = parts[1].strip()
            
            # Basic name validation - be more lenient to capture more clients
            if len(name) > 1 and any(c.isalpha() for c in name):
                # Additional cleaning for names
                name = re.sub(r'[^\w\s\'-]', '', name).strip()
                
                if len(name) > 1:
                    return {
                        'name': name,
                        'birthday': birthday,
                        'status': status,
                        'raw_line': line,
                        'confidence': 'high'
                    }
        
        # If we can't split properly, try to extract just the name with more aggressive approach
        elif line.strip():
            # More aggressive cleaning and extraction for "First Name Last Name" format
            cleaned_line = line.strip()
            
            # Remove common non-name characters but keep spaces, hyphens, apostrophes
            cleaned_line = re.sub(r'[^\w\s\'-]', ' ', cleaned_line)
            cleaned_line = ' '.join(cleaned_line.split())  # Normalize spaces
            
            if len(cleaned_line) > 1 and any(c.isalpha() for c in cleaned_line):
                words = cleaned_line.split()
                
                # For "First Name Last Name" format, we should have at least 2 words
                if len(words) >= 2:
                    # Check if words look like names (start with capital letter)
                    name_words = []
                    for word in words:
                        if word and word[0].isupper() and word.isalpha():
                            name_words.append(word)
                        elif word.lower() in ['active', 'dropout', 'na', 'inactive']:
                            # Found status, everything before this is the name
                            break
                    
                    if len(name_words) >= 2:
                        return {
                            'name': ' '.join(name_words),
                            'birthday': birthday,
                            'status': 'Unknown',
                            'raw_line': line,
                            'confidence': 'medium'
                        }
                    elif len(name_words) == 1 and len(name_words[0]) >= 3:
                        # Single word that might be a last name or incomplete name
                        return {
                            'name': name_words[0],
                            'birthday': birthday,
                            'status': 'Unknown',
                            'raw_line': line,
                            'confidence': 'low'
                        }
                
                # Fallback: if line has reasonable content, try to extract it
                elif len(words) == 1 and len(words[0]) >= 3 and words[0].isalpha():
                    return {
                        'name': words[0],
                        'birthday': birthday,
                        'status': 'Unknown',
                        'raw_line': line,
                        'confidence': 'low'
                    }
        
        return None

    def _extract_client_aggressive(self, line, birthday):
        """More aggressive extraction method specifically for 'First LastInitial' format."""
        line = line.strip()
        
        # Skip obvious non-client lines
        if not line or len(line) < 3:
            return None
            
        line_lower = line.lower()
        
        # Skip header-like content
        if any(header in line_lower for header in ['client name', 'status', 'page', 'total']):
            return None
        
        # Try multiple patterns for "First LastName Status" format
        patterns = [
            # Pattern 1: "FirstName LastName Active/Dropout" (most common)
            r'^([A-Za-z][a-z\'-]*)\s+([A-Za-z][a-z\'-]*)\s+(Active|Dropout|NA|Inactive)$',
            # Pattern 2: "FirstName LastName" without explicit status
            r'^([A-Za-z][a-z\'-]*)\s+([A-Za-z][a-z\'-]*)$',
            # Pattern 3: Handle compound first names like "Mary-Ann"
            r'^([A-Za-z][a-z\'-]*-[A-Za-z][a-z\'-]*)\s+([A-Za-z][a-z\'-]*)\s+(Active|Dropout|NA|Inactive)$',
            # Pattern 4: Handle three-part names like "Mary Ann Smith"
            r'^([A-Za-z][a-z\'-]*)\s+([A-Za-z][a-z\'-]*)\s+([A-Za-z][a-z\'-]*)\s+(Active|Dropout|NA|Inactive)$',
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                if i == 3:  # Three-part name pattern
                    first_name = match.group(1).strip()
                    middle_name = match.group(2).strip()
                    last_name = match.group(3).strip()
                    status = match.group(4).strip()
                    name = f"{first_name} {middle_name} {last_name}"
                else:
                    first_name = match.group(1).strip()
                    last_name = match.group(2).strip()
                    status = match.group(3).strip() if len(match.groups()) >= 3 else 'Unknown'
                    name = f"{first_name} {last_name}"
                
                # Proper case the names
                name = ' '.join(word.capitalize() for word in name.split())
                
                return {
                    'name': name,
                    'birthday': birthday,
                    'status': status,
                    'raw_line': line,
                    'confidence': 'high'
                }
        
        # Fallback: try to extract any two-word name pattern
        words = line.split()
        if len(words) >= 2:
            # Look for two alphabetic words that could be first and last name
            if (words[0].isalpha() and len(words[0]) >= 2 and 
                words[1].isalpha() and len(words[1]) >= 2):
                
                first_name = words[0].capitalize()
                last_name = words[1].capitalize()
                status = 'Unknown'
                
                # Check if there's a status word
                if len(words) >= 3 and words[2].lower() in ['active', 'dropout', 'na', 'inactive']:
                    status = words[2].capitalize()
                
                return {
                    'name': f"{first_name} {last_name}",
                    'birthday': birthday,
                    'status': status,
                    'raw_line': line,
                    'confidence': 'medium'
                }
        
        return None

    def _extract_any_name_like_text(self, line, birthday):
        """Ultra-aggressive extraction targeting 'FirstName LastInitial' pattern specifically."""
        line = line.strip()
        
        # Skip if obviously not a name
        if not line or len(line) < 3:
            return None
            
        # Skip common non-name patterns
        line_lower = line.lower()
        skip_patterns = ['client name', 'status', 'page', 'total', 'summary', 'date', 'birthday']
        if any(pattern in line_lower for pattern in skip_patterns):
            return None
        
        # Clean the line but preserve essential characters
        cleaned = re.sub(r'[^a-zA-Z\s\'-]', ' ', line)
        cleaned = ' '.join(cleaned.split())  # Normalize spaces
        
        if not cleaned or len(cleaned) < 3:
            return None
        
        words = cleaned.split()
        
        # Look specifically for "FirstName LastName" pattern
        if len(words) >= 2:
            first_word = words[0]
            second_word = words[1]
            
            # Check if both words look like names (alphabetic, reasonable length)
            if (first_word.isalpha() and len(first_word) >= 2 and 
                second_word.isalpha() and len(second_word) >= 2):
                
                first_name = first_word.capitalize()
                last_name = second_word.capitalize()
                
                # Look for status in remaining words
                status = 'Unknown'
                for remaining_word in words[2:]:
                    if remaining_word.lower() in ['active', 'dropout', 'na', 'inactive']:
                        status = remaining_word.capitalize()
                        break
                
                return {
                    'name': f"{first_name} {last_name}",
                    'birthday': birthday,
                    'status': status,
                    'raw_line': line,
                    'confidence': 'medium'
                }
        
        # Fallback for single names that might be incomplete
        if len(words) == 1 and words[0].isalpha() and len(words[0]) >= 3:
            return {
                'name': words[0].capitalize(),
                'birthday': birthday,
                'status': 'Unknown',
                'raw_line': line,
                'confidence': 'low'
            }
        
        return None

    def _extract_from_three_column_format(self, line):
        """Extract client data from the simple format: Name Date Status (e.g., 'Robyn K 2025-01-11 Active')."""
        
        words = line.split()
        if len(words) < 3:
            return None
        
        # Status keywords
        status_keywords = ['active', 'dropout', 'na', 'inactive']
        
        # The format is: [Name parts...] [YYYY-MM-DD] [Status]
        # Find the date (should be in YYYY-MM-DD format)
        date_idx = None
        for i, word in enumerate(words):
            if re.match(r'\d{4}-\d{1,2}-\d{1,2}', word):
                date_idx = i
                break
        
        if date_idx is None:
            return None
        
        # Everything before the date is the name
        name_parts = words[:date_idx]
        date_str = words[date_idx]
        
        # Everything after the date should be status
        status_parts = words[date_idx + 1:]
        
        if not name_parts or not status_parts:
            return None
        
        name = ' '.join(name_parts)
        status = ' '.join(status_parts)
        
        # Validate the extracted components
        # Name should have letters
        if not any(c.isalpha() for c in name) or len(name) < 2:
            return None
        
        # Status should be a known status (be flexible with case)
        if not any(status.lower().startswith(keyword) for keyword in status_keywords):
            # If status doesn't match known keywords, still extract but mark as unknown
            status = 'Unknown'
        else:
            # Normalize status
            for keyword in status_keywords:
                if status.lower().startswith(keyword):
                    status = keyword.title()
                    break
        
        return {
            'name': name,
            'birthday': date_str,
            'status': status,
            'confidence': 'high'
        }

    def _fix_missing_birthdays(self, lines, birthday_data):
        """Fix clients that are missing birthday assignments by mapping them to date sections."""
        # Create a mapping of client names to their line positions
        clients_needing_fix = []
        for i, client in enumerate(birthday_data):
            if client.get('needs_birthday_fix'):
                clients_needing_fix.append((i, client))
        
        if not clients_needing_fix:
            return birthday_data
        
        # Re-parse the document to map line positions to dates
        current_date = None
        line_to_date_map = {}
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check for date header
            date_match = self._extract_date_header(line)
            if date_match:
                current_date = date_match
                continue
            
            # Map this line to the current date
            if current_date:
                line_to_date_map[line_num] = current_date
        
        # Now try to match clients to their dates based on raw_line content
        for client_idx, client in clients_needing_fix:
            raw_line = client.get('raw_line', '').strip()
            if not raw_line:
                continue
            
            # Find the best matching line in the document
            best_date = None
            best_match_score = 0
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                if line_num in line_to_date_map:
                    # Calculate similarity between raw_line and this line
                    similarity = self._calculate_line_similarity(raw_line, line)
                    if similarity > best_match_score and similarity > 0.7:  # 70% similarity threshold
                        best_match_score = similarity
                        best_date = line_to_date_map[line_num]
            
            # Update the client with the found date
            if best_date:
                birthday_data[client_idx]['birthday'] = best_date
                birthday_data[client_idx]['needs_birthday_fix'] = False
                birthday_data[client_idx]['birthday_fix_confidence'] = best_match_score
        
        return birthday_data

    def _calculate_line_similarity(self, line1, line2):
        """Calculate similarity between two lines (simple approach)."""
        if not line1 or not line2:
            return 0.0
        
        # Normalize both lines
        line1_norm = ' '.join(line1.lower().split())
        line2_norm = ' '.join(line2.lower().split())
        
        if line1_norm == line2_norm:
            return 1.0
        
        # Check if one line contains the other
        if line1_norm in line2_norm or line2_norm in line1_norm:
            return 0.8
        
        # Count common words
        words1 = set(line1_norm.split())
        words2 = set(line2_norm.split())
        
        if not words1 or not words2:
            return 0.0
        
        common_words = words1.intersection(words2)
        total_words = words1.union(words2)
        
        return len(common_words) / len(total_words) if total_words else 0.0

    def _remove_duplicates(self, birthday_data):
        """Remove duplicate entries based on name similarity."""
        unique_data = []
        seen_names = set()
        
        for entry in birthday_data:
            name_normalized = entry['name'].lower().strip()
            
            # Simple duplicate detection
            if name_normalized not in seen_names:
                seen_names.add(name_normalized)
                unique_data.append(entry)
            else:
                # If we find a duplicate, keep the one with higher confidence
                for i, existing in enumerate(unique_data):
                    if existing['name'].lower().strip() == name_normalized:
                        if (entry.get('confidence') == 'high' and 
                            existing.get('confidence') != 'high'):
                            unique_data[i] = entry
                        break
        
        return unique_data
