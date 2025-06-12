import pandas as pd
import re
from datetime import datetime, date
from dateutil import parser as date_parser

class DataValidator:
    """Handles validation and cleaning of extracted birthday data."""
    
    def __init__(self):
        self.current_year = datetime.now().year
        self.min_birth_year = 1900
        self.max_birth_year = self.current_year
        
        # Common invalid name patterns
        self.invalid_name_patterns = [
            r'^[0-9]+$',  # Only numbers
            r'^[^a-zA-Z]+$',  # No letters
            r'^\s*$',  # Only whitespace
            r'^.{1}$',  # Single character
        ]
        
        # Common false positive names to filter out
        self.false_positive_names = {
            'Date Born', 'Birth Date', 'Client Name', 'Full Name',
            'First Last', 'Name Date', 'Page Number', 'Date Time',
            'Client List', 'Birthday List', 'Contact Info', 'Phone Number',
            'Email Address', 'Home Address', 'Work Phone', 'Cell Phone',
            'Emergency Contact', 'Next Appointment', 'Last Visit'
        }
    
    def validate_and_clean(self, raw_data):
        """
        Validate and clean the extracted birthday data.
        
        Args:
            raw_data (list): List of dictionaries with raw extracted data
            
        Returns:
            list: Cleaned and validated data
        """
        cleaned_data = []
        
        for entry in raw_data:
            cleaned_entry = self._clean_single_entry(entry)
            if cleaned_entry:
                cleaned_data.append(cleaned_entry)
        
        # Remove duplicates and merge similar entries
        cleaned_data = self._remove_duplicates_and_merge(cleaned_data)
        
        # Sort by status priority (Active, Dropout, NA) then by name within each group
        def sort_key(entry):
            status = entry.get('status', '').lower()
            name = entry.get('name', '').lower()
            
            # Define status priority order
            if status == 'active':
                priority = 1
            elif status == 'dropout':
                priority = 2
            elif status in ['na', 'inactive']:
                priority = 3
            else:
                priority = 4  # Unknown status last
            
            return (priority, name)
        
        cleaned_data.sort(key=sort_key)
        
        return cleaned_data
    
    def _clean_single_entry(self, entry):
        """Clean and validate a single data entry."""
        cleaned_entry = {}
        
        # Clean and validate name
        name = self._clean_name(entry.get('name', ''))
        if not self._is_valid_name(name):
            return None
        
        cleaned_entry['name'] = name
        
        # Clean and validate birthday
        birthday = self._clean_birthday(entry.get('birthday'))
        cleaned_entry['birthday'] = birthday
        
        # Add status information
        status = entry.get('status', 'Unknown')
        cleaned_entry['status'] = status
        
        # Add validation status
        cleaned_entry['name_valid'] = True
        cleaned_entry['birthday_valid'] = birthday is not None
        
        # Calculate age if birthday is valid
        if birthday:
            try:
                birth_date = datetime.strptime(birthday, '%Y-%m-%d').date()
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                cleaned_entry['age'] = age
            except:
                cleaned_entry['age'] = None
        else:
            cleaned_entry['age'] = None
        
        # Add metadata
        cleaned_entry['source_line'] = entry.get('raw_line', '')
        cleaned_entry['confidence'] = entry.get('confidence', 'medium')
        
        return cleaned_entry
    
    def _clean_name(self, name):
        """Clean and normalize name string."""
        if not name:
            return ""
        
        # Remove extra whitespace and normalize
        name = ' '.join(name.strip().split())
        
        # Remove common prefixes/suffixes that might be noise
        prefixes_to_remove = ['Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.']
        suffixes_to_remove = ['Jr.', 'Sr.', 'III', 'IV']
        
        words = name.split()
        cleaned_words = []
        
        for word in words:
            word_clean = word.strip('.,;:-')
            
            # Skip prefixes and suffixes
            if word_clean in prefixes_to_remove + suffixes_to_remove:
                continue
            
            # Proper case formatting
            if word_clean.isalpha():
                cleaned_words.append(word_clean.capitalize())
            else:
                cleaned_words.append(word_clean)
        
        return ' '.join(cleaned_words)
    
    def _is_valid_name(self, name):
        """Validate if the name is likely a real person's name."""
        if not name or len(name.strip()) < 2:
            return False
        
        # Check against false positives
        if name in self.false_positive_names:
            return False
        
        # Check invalid patterns
        for pattern in self.invalid_name_patterns:
            if re.match(pattern, name):
                return False
        
        # Name should have at least first and last name
        words = name.split()
        if len(words) < 2:
            return False
        
        # Each word should be reasonable length and contain letters
        for word in words:
            if len(word) < 2 or not any(c.isalpha() for c in word):
                return False
        
        # Check for common patterns that indicate false positives
        if any(indicator in name.lower() for indicator in ['phone', 'email', 'address', 'date', 'page']):
            return False
        
        return True
    
    def _clean_birthday(self, birthday):
        """Clean and validate birthday string."""
        if not birthday:
            return None
        
        try:
            # If already in YYYY-MM-DD format, validate it
            if isinstance(birthday, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', birthday):
                birth_date = datetime.strptime(birthday, '%Y-%m-%d').date()
            else:
                # Parse various date formats
                if isinstance(birthday, str):
                    birth_date = date_parser.parse(birthday, fuzzy=True).date()
                else:
                    birth_date = birthday
            
            # Validate year range
            if not (self.min_birth_year <= birth_date.year <= self.max_birth_year):
                return None
            
            # Validate month and day
            if not (1 <= birth_date.month <= 12):
                return None
            
            if not (1 <= birth_date.day <= 31):
                return None
            
            # For birthday data, allow future dates (they might be appointment dates or other relevant dates)
            # Only reject dates that are extremely far in the future (more than 5 years)
            max_future_date = date.today().replace(year=date.today().year + 5)
            if birth_date > max_future_date:
                return None
            
            return birth_date.strftime('%Y-%m-%d')
            
        except (ValueError, TypeError, OverflowError):
            return None
    
    def _remove_duplicates_and_merge(self, data):
        """Remove duplicates and merge similar entries."""
        unique_data = []
        processed_names = set()
        
        for entry in data:
            name_key = self._normalize_name_for_comparison(entry['name'])
            
            if name_key in processed_names:
                # Find the existing entry and potentially merge
                for i, existing in enumerate(unique_data):
                    existing_key = self._normalize_name_for_comparison(existing['name'])
                    if existing_key == name_key:
                        # Merge entries - keep the one with better data
                        merged = self._merge_entries(existing, entry)
                        unique_data[i] = merged
                        break
            else:
                processed_names.add(name_key)
                unique_data.append(entry)
        
        return unique_data
    
    def _normalize_name_for_comparison(self, name):
        """Normalize name for duplicate detection."""
        # Remove punctuation, convert to lowercase, remove extra spaces
        normalized = re.sub(r'[^\w\s]', '', name.lower())
        normalized = ' '.join(normalized.split())
        return normalized
    
    def _merge_entries(self, entry1, entry2):
        """Merge two similar entries, keeping the best data."""
        merged = entry1.copy()
        
        # Prefer entry with valid birthday
        if not entry1.get('birthday_valid', False) and entry2.get('birthday_valid', False):
            merged['birthday'] = entry2['birthday']
            merged['birthday_valid'] = entry2['birthday_valid']
            merged['age'] = entry2.get('age')
        
        # Prefer higher confidence
        if entry2.get('confidence') == 'high' and entry1.get('confidence') != 'high':
            merged['confidence'] = entry2['confidence']
            merged['source_line'] = entry2.get('source_line', '')
        
        # Keep the longer/more complete name
        if len(entry2['name']) > len(entry1['name']):
            merged['name'] = entry2['name']
        
        return merged
    
    def generate_data_quality_report(self, data):
        """Generate a data quality report."""
        if not data:
            return {
                'total_records': 0,
                'valid_names': 0,
                'valid_birthdays': 0,
                'missing_birthdays': 0,
                'confidence_distribution': {},
                'age_statistics': {}
            }
        
        total_records = len(data)
        valid_names = sum(1 for entry in data if entry.get('name_valid', False))
        valid_birthdays = sum(1 for entry in data if entry.get('birthday_valid', False))
        missing_birthdays = total_records - valid_birthdays
        
        # Confidence distribution
        confidence_dist = {}
        for entry in data:
            conf = entry.get('confidence', 'unknown')
            confidence_dist[conf] = confidence_dist.get(conf, 0) + 1
        
        # Age statistics
        ages = [entry.get('age') for entry in data if entry.get('age') is not None]
        age_stats = {}
        if ages:
            age_stats = {
                'min_age': min(ages),
                'max_age': max(ages),
                'avg_age': sum(ages) / len(ages),
                'count': len(ages)
            }
        
        return {
            'total_records': total_records,
            'valid_names': valid_names,
            'valid_birthdays': valid_birthdays,
            'missing_birthdays': missing_birthdays,
            'confidence_distribution': confidence_dist,
            'age_statistics': age_stats
        }
