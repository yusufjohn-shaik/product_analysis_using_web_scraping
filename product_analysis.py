# ============================================================
# Module 1 — Imports & Configuration
# ============================================================
import sys
import time
from urllib.parse import urljoin
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://scrapingsandbox.com/data-table"
MAX_PAGES = 20
TIMEOUT = 10
MIN_VENDOR_PRODUCTS = 2
HEADERS = {"User-Agent": "Mozilla/5.0"}


# ============================================================
# Module 2 — Data Fetching
# ============================================================
def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch_soup(session: requests.Session, url: str, retries: int = 3) -> BeautifulSoup:
    """GET a page with a simple retry loop, then parse it."""
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(attempt)


# ============================================================
# Module 3.1 — Cell Extraction
# ============================================================
def cell_value(cell) -> str:
    """Return cell text; if the cell holds only an image, return its src."""
    text = cell.get_text(" ", strip=True)
    if text:
        return text
    img = cell.find("img")
    if img is not None:
        return img.get("src", "")
    return ""


# ============================================================
# Module 3.2 — Table Parsing
# ============================================================
def parse_table(soup: BeautifulSoup):
    """Parse the first table. Works with or without thead/tbody."""
    table = soup.find("table")
    if table is None:
        return None, []
    rows = table.find_all("tr")
    if not rows:
        return None, []

    # Header: first row containing <th> cells
    header_cells = None
    for row in rows:
        ths = row.find_all("th")
        if ths:
            header_cells = ths
            break
    if header_cells is None:
        return None, []

    columns = [th.get_text(" ", strip=True) for th in header_cells]

    data = []
    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue
        values = [cell_value(c) for c in cells]
        if len(values) == len(columns):
            data.append(values)

    return columns, data


# ============================================================
# Module 3.3 — Pagination
# ============================================================
def find_next_url(soup: BeautifulSoup, current_url: str):
    """Look for a 'next page' link. Returns an absolute URL or None."""
    link = soup.find("a", rel="next")
    if link is None:
        for a in soup.find_all("a", href=True):
            label = a.get_text(strip=True).lower()
            if label in {"next", "next page", "next »", "»", ">"}:
                link = a
                break
    if link is None or not link.get("href"):
        return None
    if "disabled" in " ".join(link.get("class", [])).lower():
        return None
    href = link["href"]
    if href.startswith("#") or href.lower().startswith("javascript"):
        return None
    return urljoin(current_url, href)


# ============================================================
# Module 3.4 — Scraping All Pages
# ============================================================
def scrape_all_pages(start_url: str) -> pd.DataFrame:
    session = make_session()
    url = start_url
    visited = set()
    all_rows = []
    columns = None

    while url and url not in visited and len(visited) < MAX_PAGES:
        visited.add(url)
        soup = fetch_soup(session, url)
        page_columns, page_rows = parse_table(soup)
        if page_columns is None:
            if not (visited - {url}):
                raise RuntimeError("Product table not found!")
            break
        columns = columns or page_columns
        all_rows.extend(page_rows)
        print(f"Scraped {len(page_rows)} rows from {url}")
        url = find_next_url(soup, url)

    print(f"Pages fetched: {len(visited)} | Total rows: {len(all_rows)}")
    df = pd.DataFrame(all_rows, columns=columns)
    df.columns = df.columns.str.strip()
    if "ID" in df.columns:
        df = df.drop_duplicates(subset="ID").reset_index(drop=True)
    return df


# ============================================================
# Module 4 — Data Cleaning
# ============================================================
STOCK_MAP = {
    "yes": True,
    "in stock": True,
    "true": True,
    "1": True,
    "no": False,
    "out of stock": False,
    "false": False,
    "0": False,
}


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Keep only digits and decimal point
    df["Price"] = pd.to_numeric(
        df["Price"].astype(str).str.replace(r"[^\d.]", "", regex=True),
        errors="coerce",
    )

    df["Rating"] = pd.to_numeric(
        df["Rating"].astype(str).str.extract(r"(\d+(?:\.\d+)?)")[0],
        errors="coerce",
    )

    df["Variants"] = pd.to_numeric(
        df["Variants"],
        errors="coerce",
    ).astype("Int64")

    df["Stock"] = (
        df["Stock"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(STOCK_MAP)
        .astype("boolean")
    )

    for col in ["Title", "Vendor", "Category"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


# ============================================================
# Module 5.1 — Group Analysis
# ============================================================
def group_report(df: pd.DataFrame, by: str) -> pd.DataFrame:
    return (
        df.groupby(by)
        .agg(
            Product_Count=("Title", "size"),
            Average_Price=("Price", "mean"),
            Average_Rating=("Rating", "mean"),
        )
        .sort_values(
            ["Product_Count", "Average_Rating"],
            ascending=[False, False],
        )
    )


# ============================================================
# Module 5.2 & 5.3 — Statistical Analysis, Rankings & Results
# ============================================================
def analyze(df: pd.DataFrame) -> dict:
    prices = df["Price"].dropna().to_numpy()
    ratings = df["Rating"].dropna().to_numpy()

    stats = {
        "total": len(df),
        "avg_price": np.mean(prices),
        "median_price": np.median(prices),
        "min_price": np.min(prices),
        "max_price": np.max(prices),
        "std_price": np.std(prices, ddof=1),
        "avg_rating": np.mean(ratings),
        "in_stock": int((df["Stock"] == True).sum()),
        "out_of_stock": int((df["Stock"] == False).sum()),
        "stock_unknown": int(df["Stock"].isna().sum()),
    }

    category = group_report(df, "Category")
    vendor = group_report(df, "Vendor")
    vendor_ranked = vendor[
        vendor["Product_Count"] >= MIN_VENDOR_PRODUCTS
    ]

    # Top 10 expensive products
    expensive = df.sort_values(
        ["Price", "Title"],
        ascending=[False, True],
    ).head(10)

    # Top 10 rated products
    top_rated = df.sort_values(
        ["Rating", "Price", "Title"],
        ascending=[False, True, True],
    ).head(10)

    return {
        "stats": stats,
        "category": category,
        "vendor": vendor,
        "vendor_ranked": vendor_ranked,
        "expensive": expensive,
        "top_rated": top_rated,
    }


# ============================================================
# Module 6.1 & 6.2 — Printing the Report & CSV Output
# ============================================================
def print_report(results: dict) -> None:
    s = results["stats"]
    cols = [
        "Title",
        "Vendor",
        "Category",
        "Price",
        "Rating",
    ]
    print("\n" + "=" * 60)
    print("DATA ANALYSIS REPORT")
    print("=" * 60)
    print(f"\nTotal Products       : {s['total']}")
    print(f"Average Price        : ${s['avg_price']:.2f}")
    print(f"Median Price         : ${s['median_price']:.2f}")
    print(f"Minimum Price        : ${s['min_price']:.2f}")
    print(f"Maximum Price        : ${s['max_price']:.2f}")
    print(f"Price Std Deviation  : ${s['std_price']:.2f}")
    print(f"\nAverage Rating       : {s['avg_rating']:.2f}")
    print(f"\nIn Stock             : {s['in_stock']}")
    print(f"Out of Stock         : {s['out_of_stock']}")
    if s["stock_unknown"]:
        print(f"Unknown Stock Status : {s['stock_unknown']}")

    sections = [
        ("CATEGORY ANALYSIS", results["category"]),
        (
            f"VENDOR ANALYSIS (vendors with {MIN_VENDOR_PRODUCTS}+ products)",
            results["vendor_ranked"],
        ),
        (
            "TOP 10 EXPENSIVE PRODUCTS",
            results["expensive"][cols],
        ),
        (
            "TOP 10 RATED PRODUCTS",
            results["top_rated"][cols],
        ),
    ]

    for title, frame in sections:
        print("\n" + "-" * 60)
        print(title)
        print("-" * 60)
        print(frame.to_string())


def save_outputs(df: pd.DataFrame, results: dict) -> None:
    df.to_csv("scraped_products.csv", index=False)
    results["category"].to_csv(
        "category_analysis.csv"
    )
    results["vendor"].to_csv(
        "vendor_analysis.csv"
    )
    print("\nData saved successfully!")
    print("\nFiles created:")
    print("1. scraped_products.csv")
    print("2. category_analysis.csv")
    print("3. vendor_analysis.csv")


# ============================================================
# Module 7 — Visualisation
# ============================================================
import matplotlib.pyplot as plt


def plot_charts(df: pd.DataFrame, results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Chart 1: products per category
    results["category"]["Product_Count"].plot(
        kind="bar", ax=axes[0], color="steelblue")
    axes[0].set_title("Products per Category")
    axes[0].set_ylabel("Number of Products")

    # Chart 2: price distribution
    axes[1].hist(df["Price"], bins=10, color="seagreen", edgecolor="black")
    axes[1].set_title("Price Distribution")
    axes[1].set_xlabel("Price ($)")
    axes[1].set_ylabel("Frequency")

    plt.tight_layout()
    plt.savefig("analysis_charts.png")
    plt.show()


# ============================================================
# Module 8 — Main Controller
# ============================================================
def main() -> None:
    try:
        raw = scrape_all_pages(URL)
    except requests.RequestException as e:
        sys.exit(f"Failed to fetch website: {e}")
    except RuntimeError as e:
        sys.exit(str(e))

    print("\nRAW DATA")
    print(raw.head())

    df = clean_data(raw)

    print("\nMISSING VALUES AFTER CLEANING")
    print(df.isnull().sum())

    before = len(df)
    df = df.dropna(
        subset=["Price", "Rating"]
    ).reset_index(drop=True)

    if len(df) < before:
        print(
            f"Dropped {before - len(df)} rows "
            f"with missing Price/Rating"
        )

    if df.empty:
        sys.exit("No valid rows to analyze.")

    results = analyze(df)
    print_report(results)
    save_outputs(df, results)
    plot_charts(df, results)


# Run the main controller
if __name__ == "__main__":
    main()
