#CODE TO RUN IN PARALLEL

import pandas as pd
import re
import urllib.parse
from botasaurus.browser import browser, Driver

# -------------------------------
# Utility functions for extraction
# -------------------------------

def extract_google_info(driver: Driver):
    """
    Extracts Name, Address, and Phone from Google search results with error handling.
    """
    try:
        name = driver.get_text('div[data-attrid="title"]', wait=3) or None
    except Exception:
        name = None

    try:
        address = driver.get_text('span.LrzXr') or None
    except Exception:
        address = None

    try:
        phone_element = driver.get_text('span[aria-label^="Call Phone Number"]')
        phone_match = re.search(r'\(\d{3}\) \d{3}-\d{4}', phone_element)
        phone = phone_match.group(0) if phone_match else None
    except Exception:
        phone = None

    print(f"Extracted: {name}, {address}, {phone}")
    return {"name": name, "address": address, "phone": phone}

def format_google_search_url(query):
    """Formats the search query into a Google Search URL."""
    encoded_query = urllib.parse.quote_plus(query)
    return f"https://www.google.com/search?q={encoded_query}"

# -------------------------------
# Scraping function using Botasaurus Browser asynchronously
# -------------------------------

@browser(run_async=True, headless=True, parallel=10, block_images_and_css=True, reuse_driver=True)
def scrape_google_details(driver: Driver, query: str):
    """
    Searches Google for a company/town hall and extracts relevant details.
    Runs asynchronously.
    """
    try:
        # Build and open the search URL
        search_url = format_google_search_url(query)
        print(f"Searching Google for: {query}")
        driver.google_get(search_url, accept_google_cookies=True)

        # Extract and return details
        return extract_google_info(driver)
    except Exception as e:
        print(f"Error scraping details for {query}: {e}")
        return None  # Return None if any error occurs

# -------------------------------
# Main workflow: Load DataFrame and scrape details asynchronously in batches
# -------------------------------

dataframe_name = input("Enter the dataframe name: (example : df2)")
column_name = input("Enter the column name containing the search query: (example : COMPANY DETAILS)")


# Assume df2 is already defined and contains your data
df = dataframe_name  

# Initialize a DataFrame to store results
df_final = pd.DataFrame(columns=[f'{column_name}', 'name', 'address', 'phone'])

# Create an empty CSV file with headers
csv_filename = "scraped_results.csv"
df_final.to_csv(csv_filename, index=False, mode='w')

# Set batch size (number of asynchronous tasks before waiting for their results)
batch_size = 5
futures = []  # List to hold tuples of (company, future)

# Launch asynchronous scraping tasks for each company
for index, company in enumerate(df[f'{column_name}'], start=1):
    # Launch the scraping task asynchronously (returns a future)
    future = scrape_google_details(company)
    futures.append((company, future))
    
    # When batch is full or at the last record, wait for the batch results and save them
    if index % batch_size == 0 or index == len(df):
        batch_results = []  # To store non-None results
        for company, future in futures:
            details = future.get()  # Wait for the asynchronous task to complete
            if details:  # Only add non-None results
                details[f'{column_name}'] = company  # Add company name to the details
                batch_results.append(details)
                df_final.loc[len(df_final)] = details  # Append to DataFrame
        if batch_results:
            pd.DataFrame(batch_results).to_csv(csv_filename, index=False, mode='a', header=False)
            print(f"Saved {index} records to {csv_filename}")
        futures.clear()  # Clear the list for the next batch

print("Scraping completed. Results saved to CSV.")