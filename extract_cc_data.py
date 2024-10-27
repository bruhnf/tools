import pdfplumber
import csv
import re
from datetime import datetime
import os
from collections import defaultdict
import glob
import pathlib

class StatementParser:
    def __init__(self, directory):
        # Convert directory to Path object to handle spaces correctly
        self.directory = pathlib.Path(directory)
        self.transactions_by_year = defaultdict(list)
        
    def parse_amount(self, amount_str):
        """Convert amount string to float, handling credits/debits."""
        amount = amount_str.replace('$', '').replace(',', '')
        return float(amount)

    def is_date(self, text):
        """Check if text matches date format MMM DD."""
        date_pattern = r'^[A-Z][a-z]{2}\s+\d{1,2}$'
        return bool(re.match(date_pattern, text))

    def is_amount(self, text):
        """Check if text matches amount format $d,ddd.dd."""
        amount_pattern = r'^\$\d{1,3}(,\d{3})*\.\d{2}$'
        return bool(re.match(amount_pattern, text))

    def get_statement_files(self):
        """Get all PDF files matching the naming pattern in the directory."""
        # Use pathlib to handle file pattern matching
        pattern = r"[0-9]{4} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) CreditCardStatement\.pdf"
        
        # Get all PDF files and filter them using regex
        pdf_files = []
        for file in self.directory.glob("*.pdf"):
            if re.match(pattern, file.name):
                pdf_files.append(str(file))
        
        # If no files found, print debug information
        if not pdf_files:
            print("\nDebugging information:")
            all_pdfs = list(self.directory.glob("*.pdf"))
            print("All PDF files found in directory:")
            for pdf in all_pdfs:
                print(f"  - {pdf.name}")
            print(f"Pattern used: {pattern}")
            
        return pdf_files

    def extract_year_from_filename(self, filename):
        """Extract year from filename."""
        return pathlib.Path(filename).name[:4]

    def parse_statement(self, pdf_path):
        """Parse credit card statement PDF and extract transactions."""
        transactions = []
        year = self.extract_year_from_filename(pdf_path)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text_lines = page.extract_text().split('\n')
                    
                    for line in text_lines:
                        if not line.strip():
                            continue
                        
                        parts = line.split()
                        
                        if len(parts) >= 4 and self.is_date(parts[0] + ' ' + parts[1]) and self.is_amount(parts[-1]):
                            try:
                                trans_date = ' '.join(parts[0:2])
                                post_date = ' '.join(parts[2:4])
                                amount = parts[-1]
                                description = ' '.join(parts[4:-1])
                                
                                trans_date = datetime.strptime(trans_date + ' ' + year, 
                                                             '%b %d %Y').strftime('%Y-%m-%d')
                                post_date = datetime.strptime(post_date + ' ' + year, 
                                                            '%b %d %Y').strftime('%Y-%m-%d')
                                
                                transactions.append({
                                    'Transaction Date': trans_date,
                                    'Post Date': post_date,
                                    'Description': description,
                                    'Amount': self.parse_amount(amount)
                                })
                                
                            except (ValueError, IndexError) as e:
                                print(f"Warning: Couldn't parse line in {pathlib.Path(pdf_path).name}: {line}")
                                print(f"Error: {str(e)}")
                                continue
                                
        except Exception as e:
            print(f"Error processing PDF {pathlib.Path(pdf_path).name}: {str(e)}")
            return None
            
        return transactions

    def process_all_statements(self):
        """Process all PDF statements in the directory."""
        pdf_files = self.get_statement_files()
        
        if not pdf_files:
            print(f"No matching PDF files found in {self.directory}")
            return False
            
        print(f"\nFound {len(pdf_files)} PDF files to process:")
        for pdf_file in sorted(pdf_files):
            print(f"  - {pathlib.Path(pdf_file).name}")
        
        print("\nStarting processing...")
        
        for pdf_file in sorted(pdf_files):
            print(f"\nProcessing {pathlib.Path(pdf_file).name}...")
            transactions = self.parse_statement(pdf_file)
            
            if transactions:
                year = self.extract_year_from_filename(pdf_file)
                self.transactions_by_year[year].extend(transactions)
                print(f"Added {len(transactions)} transactions for {year}")
            else:
                print(f"No transactions found in {pathlib.Path(pdf_file).name}")
        
        return bool(self.transactions_by_year)

    def save_transactions_by_year(self):
        """Save transactions to separate CSV files by year."""
        if not self.transactions_by_year:
            print("No transactions to save.")
            return False
            
        for year, transactions in self.transactions_by_year.items():
            output_file = self.directory / f"{year}_transactions.csv"
            
            try:
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['Transaction Date', 'Post Date', 'Description', 'Amount']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    sorted_transactions = sorted(transactions, 
                                              key=lambda x: datetime.strptime(x['Transaction Date'], '%Y-%m-%d'))
                    for transaction in sorted_transactions:
                        writer.writerow(transaction)
                        
                print(f"Saved {len(transactions)} transactions for {year} to {output_file}")
                
            except Exception as e:
                print(f"Error saving CSV for {year}: {str(e)}")
                return False
                
        return True

def main():
    # Prompt for input directory and handle quotes if present
    directory = input("Enter the directory containing credit card statements: ").strip().strip('"\'')
    
    # Check if directory exists
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' not found.")
        return
    
    print(f"\nProcessing statements in {directory}...")
    
    # Create parser instance and process statements
    parser = StatementParser(directory)
    
    if parser.process_all_statements():
        if parser.save_transactions_by_year():
            print("\nProcessing complete!")
            
            total_transactions = sum(len(trans) for trans in parser.transactions_by_year.values())
            print(f"\nSummary:")
            print(f"Total transactions processed: {total_transactions}")
            for year in sorted(parser.transactions_by_year.keys()):
                print(f"  {year}: {len(parser.transactions_by_year[year])} transactions")
        else:
            print("Failed to save some transactions.")
    else:
        print("No transactions were processed.")

if __name__ == "__main__":
    main()
