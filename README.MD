# Product Table Scraper & Analyzer

A Python script that scrapes a product data table from a website, cleans the data, runs statistical analysis, prints a report, saves CSV outputs, and draws charts.

Target site: <https://scrapingsandbox.com/data-table>

## Features

- Fetches pages with a `requests` session and a simple retry loop (3 attempts, increasing delay)
- Parses the first HTML table, with or without `thead`/`tbody`; image-only cells return the image `src`
- Follows "next page" links (up to `MAX_PAGES`) and removes duplicate rows by `ID`
- Cleans `Price`, `Rating`, `Variants` and `Stock` into proper numeric/boolean types
- Calculates overall statistics, category and vendor summaries, and top-10 rankings
- Saves results to CSV and generates a PNG chart image

## Requirements

- Python 3.9+
- Packages: `requests`, `beautifulsoup4`, `pandas`, `numpy`, `matplotlib`

```bash
pip install requests beautifulsoup4 pandas numpy matplotlib
```

## Usage

```bash
python scraper_analysis.py
```

The script can also be run in Google Colab or Jupyter by pasting each module into its own cell and running `main()`.

## Configuration

Settings are at the top of `scraper_analysis.py`:

| Variable | Default | Purpose |
|---|---|---|
| `URL` | `https://scrapingsandbox.com/data-table` | Page to scrape |
| `MAX_PAGES` | `20` | Maximum number of pages to fetch |
| `TIMEOUT` | `10` | Request timeout in seconds |
| `MIN_VENDOR_PRODUCTS` | `2` | Minimum products for a vendor to appear in the ranked vendor report |
| `HEADERS` | `{"User-Agent": "Mozilla/5.0"}` | Headers sent with each request |

## Project Structure

| Module | Function(s) | Description |
|---|---|---|
| 1 | — | Imports and configuration |
| 2 | `make_session`, `fetch_soup` | Fetches and parses pages with retries |
| 3.1 | `cell_value` | Extracts text (or image `src`) from a cell |
| 3.2 | `parse_table` | Turns the first table into columns and rows |
| 3.3 | `find_next_url` | Finds the next-page link |
| 3.4 | `scrape_all_pages` | Loops through pages and builds a DataFrame |
| 4 | `clean_data` | Converts types and normalizes values |
| 5.1 | `group_report` | Groups by a column and summarizes count, price, rating |
| 5.2 / 5.3 | `analyze` | Computes statistics and rankings |
| 6.1 / 6.2 | `print_report`, `save_outputs` | Prints the report and writes CSVs |
| 7 | `plot_charts` | Draws and saves charts |
| 8 | `main` | Runs the whole pipeline |

## Expected Table Columns

The script expects these columns in the scraped table:

`ID`, `Title`, `Vendor`, `Category`, `Price`, `Rating`, `Variants`, `Stock`

## Output Files

| File | Contents |
|---|---|
| `scraped_products.csv` | Cleaned product data |
| `category_analysis.csv` | Product count, average price and rating per category |
| `vendor_analysis.csv` | Product count, average price and rating per vendor |
| `analysis_charts.png` | Bar chart of products per category and a price histogram |

## Report Contents

- Total products, and average, median, minimum, maximum and standard deviation of price
- Average rating
- In-stock, out-of-stock and unknown-stock counts
- Category analysis
- Vendor analysis (vendors with at least `MIN_VENDOR_PRODUCTS` products)
- Top 10 most expensive products
- Top 10 highest-rated products

## Known Limitations

- **Pagination:** only links with `rel="next"` or text like `next`, `next page`, `next »`, `»` or `>` are followed. Numbered pagination or JavaScript-loaded pages will stop after page 1.
- **Variants:** a non-whole-number value in `Variants` will raise an error when it is converted to an integer.
- **Standard deviation:** with a single product, the price standard deviation is `NaN`.
- **Vendor report:** with a small dataset, the `MIN_VENDOR_PRODUCTS` filter may hide most vendors.
- **Notebooks:** `sys.exit()` inside Colab/Jupyter shows a `SystemExit` message instead of exiting quietly.

## Notes

Please check a site's terms of service and `robots.txt` before scraping it. The default target is a sandbox site built for practice.