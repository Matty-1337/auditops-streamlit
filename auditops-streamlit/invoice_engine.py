"""
Invoice Ingestion Engine
Handles processing of invoice files from different vendors (CSV and PDF formats).
"""
import pandas as pd
import pdfplumber
from rapidfuzz import fuzz
import re
from typing import Optional, Dict, Any
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class InvoiceIngester:
    """Handles invoice file ingestion with support for CSV and PDF formats."""
    
    # Required columns for Fintech CSV processing
    FINTECH_REQUIRED_COLUMNS = [
        'Vendor Name',
        'Process Date',
        'Invoice Number',
        'Product Number',
        'Quantity',
        'Unit Cost',
        'Product Description'
    ]
    
    # Minimum fuzzy match score for PDF product matching
    MIN_MATCH_SCORE = 85
    
    def process_fintech_csv(self, file) -> pd.DataFrame:
        """
        Process CSV file from Fintech (Fast Lane).
        
        Args:
            file: File-like object or BytesIO containing CSV data
            
        Returns:
            pd.DataFrame: Cleaned DataFrame with required columns only
            
        Raises:
            ValueError: If required columns are missing
            Exception: For other processing errors
        """
        try:
            # Load CSV into pandas
            df = pd.read_csv(file)
            
            # Validate required columns exist
            missing_cols = [col for col in self.FINTECH_REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                raise ValueError(
                    f"Missing required columns in CSV: {', '.join(missing_cols)}. "
                    f"Available columns: {', '.join(df.columns)}"
                )
            
            # Filter to keep only required columns
            df_filtered = df[self.FINTECH_REQUIRED_COLUMNS].copy()
            
            # Clean Process Date column (remove timestamps, keep YYYY-MM-DD)
            if 'Process Date' in df_filtered.columns:
                df_filtered['Process Date'] = df_filtered['Process Date'].apply(
                    self._clean_date
                )
            
            logger.info(f"Successfully processed Fintech CSV: {len(df_filtered)} rows")
            return df_filtered
            
        except pd.errors.EmptyDataError:
            raise ValueError("The uploaded CSV file is empty.")
        except pd.errors.ParserError as e:
            raise ValueError(f"Error parsing CSV file: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing Fintech CSV: {str(e)}")
            raise
    
    def process_pdf_invoice(
        self, 
        file, 
        vendor_master_file_path: str
    ) -> pd.DataFrame:
        """
        Process PDF invoice file (Smart Lane).
        
        Extracts invoice data from PDF and matches products against vendor master file.
        
        Args:
            file: File-like object or BytesIO containing PDF data
            vendor_master_file_path: Path to vendor master CSV file
            
        Returns:
            pd.DataFrame: DataFrame with extracted invoice data and matched internal IDs
            
        Raises:
            FileNotFoundError: If vendor master file doesn't exist
            ValueError: If PDF extraction fails or no matches found
            Exception: For other processing errors
        """
        try:
            # Extract data from PDF
            extracted_data = self._extract_pdf_data(file)
            
            if not extracted_data:
                raise ValueError("Could not extract any data from PDF invoice.")
            
            # Load vendor master file
            try:
                master_df = pd.read_csv(vendor_master_file_path)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Vendor master file not found: {vendor_master_file_path}"
                )
            except Exception as e:
                raise ValueError(f"Error loading vendor master file: {str(e)}")
            
            # Normalize sizes and match products
            result_rows = []
            for item in extracted_data:
                matched_id = self._match_product(
                    item,
                    master_df,
                    min_score=self.MIN_MATCH_SCORE
                )
                
                # Create result row with extracted data + matched ID
                result_row = {
                    'Invoice Number': item.get('invoice_number', ''),
                    'Invoice Date': item.get('invoice_date', ''),
                    'SKU': item.get('sku', ''),
                    'Description': item.get('description', ''),
                    'Quantity': item.get('quantity', ''),
                    'Unit Price': item.get('unit_price', ''),
                    'Normalized Size (ml)': item.get('normalized_size', ''),
                    'Matched Internal ID': matched_id if matched_id else 'No Match'
                }
                result_rows.append(result_row)
            
            result_df = pd.DataFrame(result_rows)
            logger.info(f"Successfully processed PDF invoice: {len(result_df)} items, "
                       f"{len([r for r in result_rows if r['Matched Internal ID'] != 'No Match'])} matches")
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error processing PDF invoice: {str(e)}")
            raise
    
    def _clean_date(self, date_value: Any) -> str:
        """
        Clean date value to YYYY-MM-DD format.
        
        Args:
            date_value: Date value (string, datetime, etc.)
            
        Returns:
            str: Date in YYYY-MM-DD format
        """
        if pd.isna(date_value):
            return ''
        
        # Convert to string if not already
        date_str = str(date_value)
        
        # Try parsing with pandas (handles various formats)
        try:
            parsed_date = pd.to_datetime(date_str)
            return parsed_date.strftime('%Y-%m-%d')
        except:
            # If parsing fails, try simple regex extraction
            # Look for YYYY-MM-DD pattern
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
            if date_match:
                return date_match.group(1)
            
            # Return original if we can't parse
            return date_str.strip()
    
    def _extract_pdf_data(self, file) -> list:
        """
        Extract invoice data from PDF.
        
        Args:
            file: File-like object or BytesIO containing PDF data
            
        Returns:
            list: List of dictionaries containing extracted invoice items
        """
        extracted_items = []
        
        try:
            # Read PDF with pdfplumber
            with pdfplumber.open(file) as pdf:
                invoice_number = None
                invoice_date = None
                
                # Extract header information (invoice number, date) from first page
                if len(pdf.pages) > 0:
                    first_page = pdf.pages[0]
                    text = first_page.extract_text()
                    
                    # Extract invoice number (common patterns)
                    invoice_num_match = re.search(
                        r'(?:Invoice\s*#?|Invoice\s*Number|INVOICE\s*NO\.?)\s*:?\s*([A-Z0-9\-]+)',
                        text,
                        re.IGNORECASE
                    )
                    if invoice_num_match:
                        invoice_number = invoice_num_match.group(1).strip()
                    
                    # Extract invoice date (common patterns)
                    date_match = re.search(
                        r'(?:Date|Invoice\s*Date)\s*:?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
                        text,
                        re.IGNORECASE
                    )
                    if date_match:
                        invoice_date = date_match.group(1).strip()
                
                # Extract table data from all pages
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        # Assume first row is header, try to identify column positions
                        header_row = table[0]
                        
                        # Find column indices (flexible matching)
                        sku_idx = self._find_column_index(header_row, ['sku', 'item', 'product number', 'code'])
                        desc_idx = self._find_column_index(header_row, ['description', 'product', 'item description'])
                        qty_idx = self._find_column_index(header_row, ['qty', 'quantity', 'qty.', 'qty:'])
                        price_idx = self._find_column_index(header_row, ['price', 'unit price', 'unit cost', 'cost'])
                        size_idx = self._find_column_index(header_row, ['size', 'volume', 'ml', 'ml:', 'size (ml)'])
                        
                        # Process data rows
                        for row in table[1:]:
                            # Get max index for validation
                            indices = [idx for idx in [sku_idx, desc_idx, qty_idx, price_idx] if idx is not None]
                            max_idx = max(indices) if indices else 0
                            if not row or len(row) <= max_idx:
                                continue
                            
                            sku = self._safe_get(row, sku_idx, '').strip()
                            description = self._safe_get(row, desc_idx, '').strip()
                            quantity = self._safe_get(row, qty_idx, '').strip()
                            unit_price = self._safe_get(row, price_idx, '').strip()
                            size = self._safe_get(row, size_idx, '').strip()
                            
                            # Skip empty rows
                            if not description and not sku:
                                continue
                            
                            # Normalize size
                            normalized_size = self._normalize_size(size if size else description)
                            
                            extracted_items.append({
                                'invoice_number': invoice_number,
                                'invoice_date': invoice_date,
                                'sku': sku,
                                'description': description,
                                'quantity': quantity,
                                'unit_price': unit_price,
                                'size': size,
                                'normalized_size': normalized_size
                            })
        
        except Exception as e:
            logger.error(f"Error extracting PDF data: {str(e)}")
            raise ValueError(f"Failed to extract data from PDF: {str(e)}")
        
        return extracted_items
    
    def _find_column_index(self, header_row: list, search_terms: list) -> Optional[int]:
        """Find column index by searching for keywords in header row."""
        if not header_row:
            return None
        
        for idx, cell in enumerate(header_row):
            if cell:
                cell_lower = str(cell).lower().strip()
                for term in search_terms:
                    if term.lower() in cell_lower:
                        return idx
        
        return None
    
    def _safe_get(self, row: list, index: Optional[int], default: str = '') -> str:
        """Safely get value from row by index."""
        if index is None or index >= len(row):
            return default
        value = row[index]
        return str(value) if value is not None else default
    
    def _normalize_size(self, size_str: str) -> Optional[int]:
        """
        Normalize size string to integer (ml).
        
        Converts sizes like "750ML", "1 L", "750 ml" to integers (750, 1000, 750).
        
        Args:
            size_str: Size string to normalize
            
        Returns:
            int: Normalized size in ml, or None if cannot be parsed
        """
        if not size_str:
            return None
        
        # Clean the string
        size_str = str(size_str).upper().strip()
        
        # Remove common prefixes/suffixes
        size_str = re.sub(r'[^\d.\sLMKGT]', '', size_str)
        
        # Pattern matching for various formats
        # Match: "750ML", "750 ML", "750ml" -> 750
        ml_match = re.search(r'(\d+(?:\.\d+)?)\s*ML', size_str)
        if ml_match:
            return int(float(ml_match.group(1)))
        
        # Match: "1 L", "1.5L", "1L" -> convert to ml
        liter_match = re.search(r'(\d+(?:\.\d+)?)\s*L', size_str)
        if liter_match:
            liters = float(liter_match.group(1))
            return int(liters * 1000)
        
        # Match: "750" (assume ml if no unit)
        num_match = re.search(r'(\d+(?:\.\d+)?)', size_str)
        if num_match:
            # If number is > 100, assume ml; otherwise assume liters
            value = float(num_match.group(1))
            if value > 100:
                return int(value)
            else:
                return int(value * 1000)
        
        return None
    
    def _match_product(
        self,
        item: Dict[str, Any],
        master_df: pd.DataFrame,
        min_score: int = 85
    ) -> Optional[str]:
        """
        Match PDF item to vendor master file product.
        
        Args:
            item: Dictionary containing item data (description, normalized_size, etc.)
            master_df: DataFrame containing vendor master products
            min_score: Minimum fuzzy match score (0-100)
            
        Returns:
            Optional[str]: Matched internal ID, or None if no match found
        """
        if master_df.empty:
            return None
        
        item_description = item.get('description', '')
        item_size = item.get('normalized_size')
        
        if not item_description:
            return None
        
        # Filter master by normalized size if available
        filtered_master = master_df.copy()
        
        if item_size is not None and 'Size (ml)' in master_df.columns:
            # Filter to same size
            filtered_master = filtered_master[
                filtered_master['Size (ml)'] == item_size
            ]
        elif item_size is not None and 'Normalized Size' in master_df.columns:
            filtered_master = filtered_master[
                filtered_master['Normalized Size'] == item_size
            ]
        
        if filtered_master.empty:
            # No size match, use full master
            filtered_master = master_df.copy()
        
        # Find best match using fuzzy string matching
        best_score = 0
        best_match_id = None
        
        # Determine product name column in master file
        product_name_col = None
        for col in ['Product Name', 'Name', 'Description', 'Product Description']:
            if col in filtered_master.columns:
                product_name_col = col
                break
        
        if not product_name_col:
            logger.warning("Could not find product name column in master file")
            return None
        
        # Determine ID column in master file
        id_col = None
        for col in ['Internal ID', 'ID', 'Product ID', 'SKU', 'Product Number']:
            if col in filtered_master.columns:
                id_col = col
                break
        
        if not id_col:
            logger.warning("Could not find ID column in master file")
            return None
        
        # Calculate fuzzy match scores
        for _, master_row in filtered_master.iterrows():
            master_product_name = str(master_row[product_name_col])
            
            # Use token_set_ratio for better matching (handles word order differences)
            score = fuzz.token_set_ratio(item_description, master_product_name)
            
            if score > best_score and score >= min_score:
                best_score = score
                best_match_id = str(master_row[id_col])
        
        return best_match_id

