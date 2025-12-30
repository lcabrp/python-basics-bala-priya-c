"""
Sample Data Generator for Large Dataset Tutorial
Run this script to create the sample CSV files used in the tutorial examples.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import gzip
import shutil


def _default_data_path() -> Path:
    """Return the default output folder for generated CSVs.

    We default to the directory *containing this script* so generated files stay
    self-contained next to the tutorial code.

    Note: In some interactive contexts (rare), ``__file__`` may be undefined.
    In that case we fall back to the current working directory.
    """

    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


# Default output folder for all datasets (can be overridden via folder=...)
data_path = _default_data_path()


def _gzip_csv_copy(csv_path: Path, *, remove_original: bool = False) -> Path:
    """Create a `.csv.gz` copy next to `csv_path`.

    Why this exists (tutorial note)
    ------------------------------
    CSV is a plain-text format, so "using smaller dtypes" does **not** usually
    reduce file size much by itself (because numbers/strings are still written
    as text). Compression, however, often shrinks large CSVs dramatically,
    especially when they contain repetitive columns (e.g., region/channel).

    This helper lets you:
    - keep uncompressed `.csv` for fast local use and existing notebooks
    - commit the smaller `.csv.gz` files to GitHub (often < 100MB)

    Parameters
    ----------
    csv_path : pathlib.Path
        Path to the uncompressed CSV.
    remove_original : bool, optional
        If True, delete the original `.csv` after creating the `.csv.gz` copy.
        Defaults to False (safer for tutorials).

    Returns
    -------
    pathlib.Path
        Path to the compressed `.csv.gz`.
    """

    csv_path = Path(csv_path)
    gz_path = csv_path.with_suffix(csv_path.suffix + '.gz')

    # Stream the compression to avoid loading the file into memory.
    with csv_path.open('rb') as src, gzip.open(gz_path, 'wb') as dst:
        shutil.copyfileobj(src, dst)

    if remove_original:
        csv_path.unlink(missing_ok=True)

    return gz_path


def create_sales_dataset(
    folder: Path = data_path,
    csv_file: str = 'large_sales_data.csv',
    num_rows: int = 1_000_000,
    *,
    seed: int = 42,
    chunk_size: int = 200_000,
    num_products: int = 10_000,
    num_customers: int = 500_000,
    num_stores: int = 500,
    start_date: str = '2024-01-01',
    days: int = 366,
    seasonality: bool = True,
):
    """Create the large sales CSV used by the tutorial examples.

    This function intentionally generates a *large* dataset for tutorials about
    working with large files (chunked reads, dtype optimization, aggregation,
    etc.).

    What's new vs the original version
    -------------------------------
    - **Faster dates**: generates dates using NumPy instead of a Python loop.
    - **More realistic distributions**:
      - ``product_id`` follows a long-tail popularity distribution.
      - ``revenue`` is derived from unit price, quantity, and discount.
    - **Richer schema**: adds columns that enable joins and more realistic
      analysis (e.g., customer/store/channel).
    - **Lower peak memory**: writes the CSV incrementally in chunks.

    Parameters
    ----------
    folder : pathlib.Path, optional
        Destination folder where the CSV will be written. Defaults to the
        current working directory (``Path.cwd()``).
    csv_file : str, optional
        Output filename for the generated dataset.
    num_rows : int, optional
        Number of rows (transactions) to generate.
    seed : int, optional
        Random seed used for reproducible generation.
    chunk_size : int, optional
        Rows written per chunk.
    num_products : int, optional
        Number of distinct products (controls product_id domain).
    num_customers : int, optional
        Number of distinct customers (controls customer_id domain).
    num_stores : int, optional
        Number of distinct stores (controls store_id domain).
    start_date : str, optional
        First date in the simulated calendar window (ISO format, e.g. "2024-01-01").
    days : int, optional
        Number of days in the simulated calendar window.
    seasonality : bool, optional
        If True, dates are sampled with simple seasonal patterns (weekday +
        month effects). If False, dates are uniform.

    Returns
    -------
    pathlib.Path
        Path to the generated CSV.

    Notes
    -----
    - This function uses NumPy's modern random generator for reproducibility.
    - Chunked writing keeps memory usage stable even for very large files.
    """

    # ============================================================================
    # 1. Generate large_sales_data.csv (for chunking example)
    # ============================================================================
    print(f"1. Creating {csv_file}...")

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    output_path = folder / csv_file

    # ------------------------------------------------------------------------
    # OLD VERSION (kept for the tutorial)
    # ------------------------------------------------------------------------
    # The original implementation was intentionally simple, but it has two big
    # drawbacks when scaling up:
    # 1) Date generation used a Python loop -> slow for millions of rows.
    # 2) It built the entire DataFrame in memory -> high peak RAM.
    #
    # np.random.seed(42)
    # sales_data = {
    #     'transaction_id': range(1, num_rows + 1),
    #     'date': [datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))
    #             for _ in range(num_rows)],
    #     'revenue': np.random.uniform(10, 1000, num_rows).round(2),
    #     'product_id': np.random.randint(1, 1000, num_rows),
    #     'region': np.random.choice(
    #         ['North', 'NorthEast', 'NorthWest', 'South', 'SouthEast', 'SouthWest', 'East', 'West'],
    #         num_rows,
    #     ),
    # }
    # df_sales = pd.DataFrame(sales_data)
    # df_sales.to_csv(output_path, index=False)

    # ------------------------------------------------------------------------
    # NEW VERSION
    # ------------------------------------------------------------------------
    # We generate + write in chunks to keep memory stable and to make the data
    # more realistic for downstream examples.

    if num_rows <= 0:
        raise ValueError("num_rows must be > 0")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if num_products <= 0 or num_customers <= 0 or num_stores <= 0:
        raise ValueError("num_products/num_customers/num_stores must be > 0")
    if days <= 0:
        raise ValueError("days must be > 0")

    rng = np.random.default_rng(seed)

    # ---- 1) Product popularity: long-tail distribution ----------------------
    # A small number of products are "bestsellers" and appear far more often.
    # We model this by sampling from a Pareto-like distribution and converting
    # it into probabilities.
    product_ids = np.arange(1, num_products + 1)
    popularity = rng.pareto(a=1.25, size=num_products) + 1.0
    product_prob = popularity / popularity.sum()

    # ---- 2) Product price table: stable price per product -------------------
    # Prices are usually right-skewed (many inexpensive items, a few expensive).
    product_unit_price = rng.lognormal(mean=3.5, sigma=0.7, size=num_products)
    product_unit_price = np.clip(product_unit_price, 5, 500).round(2)

    # ---- 3) Categorical columns with non-uniform probabilities --------------
    # Real data often has imbalanced categories (some regions/channels dominate).
    regions = np.array(['North', 'NorthEast', 'NorthWest', 'South', 'SouthEast', 'SouthWest', 'East', 'West'])
    region_prob = np.array([0.18, 0.08, 0.07, 0.18, 0.08, 0.07, 0.17, 0.17])

    channels = np.array(['online', 'store', 'marketplace'])
    channel_prob = np.array([0.55, 0.35, 0.10])

    # ---- 4) Vectorized date generation (with optional seasonality) ----------
    # Generate random days since a start date using NumPy.
    #
    # Why seasonality?
    # Real sales are not uniformly distributed across the calendar.
    # Even a simple set of weights (weekday + month effects) makes later
    # tutorials (groupby by month, trend charts, anomaly detection) feel more
    # realistic.
    start_date_np = np.datetime64(start_date)
    day_index = np.arange(days)
    calendar = start_date_np + day_index.astype('timedelta64[D]')

    if seasonality:
        # Weekday weights (Mon..Sun). Sales commonly rise on Fri-Sun.
        weekday = ((calendar.astype('datetime64[D]').astype('int64') + 4) % 7).astype(int)
        weekday_weights = np.array([0.95, 0.95, 1.00, 1.02, 1.08, 1.15, 1.12])

        # Month weights (Jan..Dec). Slight lift in Nov/Dec.
        month = (calendar.astype('datetime64[M]') - calendar.astype('datetime64[Y]')).astype(int) + 1
        month_weights = np.array([1.00, 0.98, 1.00, 1.01, 1.02, 1.03, 1.02, 1.02, 1.03, 1.05, 1.12, 1.15])

        weights = weekday_weights[weekday] * month_weights[month - 1]
        date_prob = (weights / weights.sum()).astype(float)
    else:
        date_prob = None

    # ---- 5) Chunked write --------------------------------------------------
    # Write header once, then append subsequent chunks.
    wrote_header = False

    for start_txn_id in range(1, num_rows + 1, chunk_size):
        chunk_rows = min(chunk_size, num_rows - start_txn_id + 1)
        transaction_id = np.arange(start_txn_id, start_txn_id + chunk_rows)

        # Dates: fast vectorized offsets
        if date_prob is None:
            day_offsets = rng.integers(0, days, size=chunk_rows)
        else:
            # Weighted sampling of days to reflect simple seasonality.
            day_offsets = rng.choice(day_index, size=chunk_rows, replace=True, p=date_prob)

        date = start_date_np + day_offsets.astype('timedelta64[D]')

        # Dimensions (good for joins and realistic groupbys)
        product_id = rng.choice(product_ids, size=chunk_rows, p=product_prob)
        customer_id = rng.integers(1, num_customers + 1, size=chunk_rows)
        store_id = rng.integers(1, num_stores + 1, size=chunk_rows)
        region = rng.choice(regions, size=chunk_rows, p=region_prob)
        channel = rng.choice(channels, size=chunk_rows, p=channel_prob)

        # Transaction mechanics
        quantity = rng.integers(1, 6, size=chunk_rows)  # 1..5 units per order line
        unit_price = product_unit_price[product_id - 1]

        # Discounts: many small discounts, rare larger discounts
        discount_rate = rng.beta(a=2.0, b=20.0, size=chunk_rows)
        discount_rate = np.clip(discount_rate, 0, 0.60)

        # Revenue: derived, not arbitrary
        revenue = (quantity * unit_price * (1.0 - discount_rate)).round(2)

        df_sales_chunk = pd.DataFrame(
            {
                'transaction_id': transaction_id,
                'date': pd.to_datetime(date),
                'customer_id': customer_id,
                'store_id': store_id,
                'channel': channel,
                'region': region,
                'product_id': product_id,
                'quantity': quantity,
                'unit_price': unit_price,
                'discount_rate': discount_rate.round(4),
                'revenue': revenue,
            }
        )

        df_sales_chunk.to_csv(
            output_path,
            mode='w' if not wrote_header else 'a',
            header=not wrote_header,
            index=False,
        )
        wrote_header = True

    print(
        f"   ✓ Created with {num_rows:,} rows "
        f"({output_path.stat().st_size / 1024**2:.1f} MB on disk)"
    )

    return output_path


def create_customers_dataset(
    folder: Path = data_path,
    csv_file: str = 'customers.csv',
    num_rows: int = 500_000,
    *,
    seed: int = 42,
    chunk_size: int = 200_000,
    start_customer_id: int = 1,
    start_date: str = '2019-01-01',
    days: int = 6 * 365,
):
    """Create a large customer table (used for column-selection examples).

    What's new vs the original version
    -------------------------------
    - Generates data in chunks to reduce peak memory.
    - Uses NumPy's RNG (reproducible) and vectorized string building.
    - Adds a couple of realistic columns (signup_date, loyalty_tier) while
      keeping the original tutorial columns intact.

    Notes
    -----
    The original tutorial version intentionally used Python list comprehensions
    to keep it readable, but for 500k+ rows those loops are noticeably slower.
    """

    print(f"2. Creating {csv_file}...")

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    output_path = folder / csv_file

    # ------------------------------------------------------------------------
    # OLD VERSION (kept for the tutorial)
    # ------------------------------------------------------------------------
    # num_customers = 500_000
    # np.random.seed(42)
    # customers_data = {
    #     'customer_id': range(1, num_customers + 1),
    #     'age': np.random.randint(18, 80, num_customers),
    #     'purchase_amount': np.random.uniform(5, 500, num_customers).round(2),
    #     'first_name': [f'User{i}' for i in range(num_customers)],
    #     'last_name': [f'Lastname{i}' for i in range(num_customers)],
    #     'email': [f'user{i}@example.com' for i in range(num_customers)],
    #     'phone': [f'555-{random.randint(1000, 9999)}' for _ in range(num_customers)],
    #     'address': [f'{random.randint(1, 9999)} Main St' for _ in range(num_customers)],
    #     'city': np.random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston'], num_customers),
    #     'state': np.random.choice(['NY', 'CA', 'IL', 'TX'], num_customers),
    #     'zip_code': [f'{random.randint(10000, 99999)}' for _ in range(num_customers)],
    # }
    # pd.DataFrame(customers_data).to_csv(output_path, index=False)

    # ------------------------------------------------------------------------
    # NEW VERSION
    # ------------------------------------------------------------------------
    if num_rows <= 0:
        raise ValueError("num_rows must be > 0")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if start_customer_id <= 0:
        raise ValueError("start_customer_id must be > 0")
    if days <= 0:
        raise ValueError("days must be > 0")

    rng = np.random.default_rng(seed)
    wrote_header = False

    cities = np.array(['New York', 'Los Angeles', 'Chicago', 'Houston'])
    city_prob = np.array([0.35, 0.25, 0.20, 0.20])
    state_by_city = {
        'New York': 'NY',
        'Los Angeles': 'CA',
        'Chicago': 'IL',
        'Houston': 'TX',
    }
    tiers = np.array(['bronze', 'silver', 'gold', 'platinum'])
    tier_prob = np.array([0.55, 0.28, 0.14, 0.03])

    start_date_np = np.datetime64(start_date)
    day_index = np.arange(days)

    for chunk_start in range(0, num_rows, chunk_size):
        chunk_rows = min(chunk_size, num_rows - chunk_start)
        customer_id = np.arange(start_customer_id + chunk_start, start_customer_id + chunk_start + chunk_rows)

        # Ages: approximate real-ish adult population distribution
        age = rng.normal(loc=41, scale=14, size=chunk_rows).round().astype(int)
        age = np.clip(age, 18, 80)

        # Purchase amount: right-skewed
        purchase_amount = rng.lognormal(mean=4.1, sigma=0.75, size=chunk_rows)
        purchase_amount = np.clip(purchase_amount, 5, 500).round(2)

        # Signup date: random within a window
        signup_day_offsets = rng.integers(0, days, size=chunk_rows)
        signup_date = start_date_np + signup_day_offsets.astype('timedelta64[D]')

        city = rng.choice(cities, size=chunk_rows, p=city_prob)
        state = np.array([state_by_city[c] for c in city], dtype=object)

        # Vectorized string construction (avoids Python loops over 500k rows)
        customer_id_str = customer_id.astype(str)
        first_name = np.char.add('User', customer_id_str)
        last_name = np.char.add('Lastname', customer_id_str)
        email = np.char.add(np.char.add('user', customer_id_str), '@example.com')

        phone_suffix = rng.integers(0, 10_000, size=chunk_rows)
        phone = np.char.add('555-', np.char.zfill(phone_suffix.astype(str), 4))

        street_num = rng.integers(1, 10_000, size=chunk_rows)
        address = np.char.add(np.char.add(street_num.astype(str), ' Main St'), '')

        zip_int = rng.integers(10_000, 100_000, size=chunk_rows)
        zip_code = np.char.zfill(zip_int.astype(str), 5)

        loyalty_tier = rng.choice(tiers, size=chunk_rows, p=tier_prob)

        df_customers_chunk = pd.DataFrame(
            {
                'customer_id': customer_id,
                'age': age,
                'purchase_amount': purchase_amount,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'address': address,
                'city': city,
                'state': state,
                'zip_code': zip_code,
                'signup_date': pd.to_datetime(signup_date),
                'loyalty_tier': loyalty_tier,
            }
        )

        df_customers_chunk.to_csv(
            output_path,
            mode='w' if not wrote_header else 'a',
            header=not wrote_header,
            index=False,
        )
        wrote_header = True

    print(f"   ✓ Created with {num_rows:,} rows ({output_path.stat().st_size / 1024**2:.1f} MB on disk)")
    return output_path


def create_ratings_dataset(
    folder: Path = data_path,
    csv_file: str = 'ratings.csv',
    num_rows: int = 2_000_000,
    *,
    seed: int = 42,
    chunk_size: int = 250_000,
    num_users: int = 500_000,
    num_products: int = 10_000,
    start_date: str = '2024-01-01',
    days: int = 366,
    seasonality: bool = True,
):
    """Create a large ratings table (used for dtype-optimization examples).

    Keeps the original columns (user_id, product_id, rating, timestamp) but:
    - generates timestamps with NumPy (no Python loop)
    - writes the CSV in chunks
    - uses a more realistic rating distribution (more 4s/5s)
    """

    print(f"3. Creating {csv_file}...")

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    output_path = folder / csv_file

    # ------------------------------------------------------------------------
    # OLD VERSION (kept for the tutorial)
    # ------------------------------------------------------------------------
    # num_ratings = 2_000_000
    # np.random.seed(42)
    # ratings_data = {
    #     'user_id': np.random.randint(1, 100000, num_ratings),
    #     'product_id': np.random.randint(1, 10000, num_ratings),
    #     'rating': np.random.randint(1, 6, num_ratings),
    #     'timestamp': [datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))
    #                   for _ in range(num_ratings)]
    # }
    # pd.DataFrame(ratings_data).to_csv(output_path, index=False)

    # ------------------------------------------------------------------------
    # NEW VERSION
    # ------------------------------------------------------------------------
    if num_rows <= 0:
        raise ValueError("num_rows must be > 0")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if num_users <= 0 or num_products <= 0:
        raise ValueError("num_users/num_products must be > 0")
    if days <= 0:
        raise ValueError("days must be > 0")

    rng = np.random.default_rng(seed)
    wrote_header = False

    start_ts = np.datetime64(f"{start_date}T00:00:00")
    day_index = np.arange(days)

    if seasonality:
        # Simple weekday lift to mimic higher engagement on weekends.
        calendar = np.datetime64(start_date) + day_index.astype('timedelta64[D]')
        weekday = ((calendar.astype('datetime64[D]').astype('int64') + 4) % 7).astype(int)
        weekday_weights = np.array([1.00, 1.00, 1.00, 1.02, 1.05, 1.10, 1.08])
        date_prob = (weekday_weights[weekday] / weekday_weights[weekday].sum()).astype(float)
    else:
        date_prob = None

    rating_values = np.array([1, 2, 3, 4, 5])
    rating_prob = np.array([0.05, 0.08, 0.17, 0.35, 0.35])

    for row_start in range(0, num_rows, chunk_size):
        chunk_rows = min(chunk_size, num_rows - row_start)

        user_id = rng.integers(1, num_users + 1, size=chunk_rows)
        product_id = rng.integers(1, num_products + 1, size=chunk_rows)
        rating = rng.choice(rating_values, size=chunk_rows, p=rating_prob)

        if date_prob is None:
            day_offsets = rng.integers(0, days, size=chunk_rows)
        else:
            day_offsets = rng.choice(day_index, size=chunk_rows, replace=True, p=date_prob)

        # Add random time-of-day (seconds)
        seconds = rng.integers(0, 24 * 60 * 60, size=chunk_rows)
        timestamp = start_ts + day_offsets.astype('timedelta64[D]') + seconds.astype('timedelta64[s]')

        df_ratings_chunk = pd.DataFrame(
            {
                'user_id': user_id,
                'product_id': product_id,
                'rating': rating,
                'timestamp': pd.to_datetime(timestamp),
            }
        )

        df_ratings_chunk.to_csv(
            output_path,
            mode='w' if not wrote_header else 'a',
            header=not wrote_header,
            index=False,
        )
        wrote_header = True

    print(f"   ✓ Created with {num_rows:,} rows ({output_path.stat().st_size / 1024**2:.1f} MB on disk)")
    return output_path


def create_products_dataset(
    folder: Path = data_path,
    csv_file: str = 'products.csv',
    num_rows: int = 5_000_000,
    *,
    seed: int = 42,
    chunk_size: int = 500_000,
):
    """Create a large product catalog (used for categorical data examples).

    Keeps the original columns (product_id, category, price, stock) but:
    - uses a right-skewed price distribution (lognormal)
    - writes in chunks to avoid huge peak memory
    - adds a couple of common catalog columns (brand, is_active)
    """

    print(f"4. Creating {csv_file}...")

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    output_path = folder / csv_file

    # ------------------------------------------------------------------------
    # OLD VERSION (kept for the tutorial)
    # ------------------------------------------------------------------------
    # num_products = 5_000_000
    # np.random.seed(42)
    # categories = [...]
    # products_data = {
    #     'product_id': range(1, num_products + 1),
    #     'category': np.random.choice(categories, num_products),
    #     'price': np.random.uniform(5, 500, num_products).round(2),
    #     'stock': np.random.randint(0, 1000, num_products)
    # }
    # pd.DataFrame(products_data).to_csv(output_path, index=False)

    # ------------------------------------------------------------------------
    # NEW VERSION
    # ------------------------------------------------------------------------
    if num_rows <= 0:
        raise ValueError("num_rows must be > 0")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")

    rng = np.random.default_rng(seed)
    wrote_header = False

    # Only 20 unique categories to demonstrate categorical efficiency
    categories = np.array(
        [
            'Electronics', 'Clothing', 'Home & Garden', 'Sports', 'Books',
            'Toys', 'Food', 'Beauty', 'Automotive', 'Health',
            'Office', 'Pet Supplies', 'Baby', 'Jewelry', 'Tools',
            'Music', 'Movies', 'Games', 'Crafts', 'Outdoor',
        ]
    )

    # Categories are not uniformly distributed in most catalogs.
    category_prob = np.array(
        [
            0.12, 0.10, 0.08, 0.06, 0.05,
            0.05, 0.06, 0.05, 0.04, 0.05,
            0.04, 0.04, 0.03, 0.03, 0.04,
            0.04, 0.03, 0.04, 0.03, 0.07,
        ]
    )
    category_prob = category_prob / category_prob.sum()

    brands = np.array(['Acme', 'Contoso', 'Globex', 'Umbrella', 'Initech', 'Soylent', 'Stark', 'Wayne'])
    brand_prob = np.array([0.22, 0.18, 0.14, 0.10, 0.10, 0.08, 0.10, 0.08])

    for chunk_start in range(0, num_rows, chunk_size):
        chunk_rows = min(chunk_size, num_rows - chunk_start)
        product_id = np.arange(1 + chunk_start, 1 + chunk_start + chunk_rows)

        category = rng.choice(categories, size=chunk_rows, p=category_prob)
        brand = rng.choice(brands, size=chunk_rows, p=brand_prob)

        # Price: right-skewed distribution; clipped to tutorial-friendly range.
        price = rng.lognormal(mean=3.6, sigma=0.75, size=chunk_rows)
        price = np.clip(price, 5, 500).round(2)

        # Stock: many small values, some larger. Poisson is a decent toy model.
        stock = rng.poisson(lam=50, size=chunk_rows)
        stock = np.clip(stock, 0, 1000).astype(int)

        is_active = rng.random(size=chunk_rows) < 0.96

        df_products_chunk = pd.DataFrame(
            {
                'product_id': product_id,
                'category': category,
                'price': price,
                'stock': stock,
                'brand': brand,
                'is_active': is_active.astype(int),
            }
        )

        df_products_chunk.to_csv(
            output_path,
            mode='w' if not wrote_header else 'a',
            header=not wrote_header,
            index=False,
        )
        wrote_header = True

    print(f"   ✓ Created with {num_rows:,} rows ({output_path.stat().st_size / 1024**2:.1f} MB on disk)")
    return output_path


def create_transactions_dataset(
    folder: Path = data_path,
    csv_file: str = 'transactions.csv',
    num_rows: int = 3_000_000,
    *,
    seed: int = 42,
    chunk_size: int = 250_000,
    num_customers: int = 500_000,
    num_products: int = 10_000,
    year_prob: tuple[float, float, float] = (0.3, 0.3, 0.4),
):
    """Create a transactions table (used for filtering examples).

    Keeps original columns (transaction_id, year, customer_id, amount, product_id)
    and adds a realistic ``transaction_date`` and ``payment_method``.
    """

    print(f"5. Creating {csv_file}...")

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    output_path = folder / csv_file

    # ------------------------------------------------------------------------
    # OLD VERSION (kept for the tutorial)
    # ------------------------------------------------------------------------
    # num_transactions = 3_000_000
    # np.random.seed(42)
    # transactions_data = {
    #     'transaction_id': range(1, num_transactions + 1),
    #     'year': np.random.choice([2022, 2023, 2024], num_transactions, p=[0.3, 0.3, 0.4]),
    #     'customer_id': np.random.randint(1, 100000, num_transactions),
    #     'amount': np.random.uniform(10, 1000, num_transactions).round(2),
    #     'product_id': np.random.randint(1, 10000, num_transactions)
    # }
    # pd.DataFrame(transactions_data).to_csv(output_path, index=False)

    # ------------------------------------------------------------------------
    # NEW VERSION
    # ------------------------------------------------------------------------
    if num_rows <= 0:
        raise ValueError("num_rows must be > 0")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if num_customers <= 0 or num_products <= 0:
        raise ValueError("num_customers/num_products must be > 0")
    if len(year_prob) != 3:
        raise ValueError("year_prob must have 3 elements for years 2022/2023/2024")

    rng = np.random.default_rng(seed)
    wrote_header = False

    years = np.array([2022, 2023, 2024])
    year_prob_arr = np.array(year_prob, dtype=float)
    year_prob_arr = year_prob_arr / year_prob_arr.sum()

    payment_methods = np.array(['card', 'cash', 'paypal', 'bank_transfer'])
    payment_prob = np.array([0.62, 0.12, 0.18, 0.08])

    # Precompute per-year constants to generate dates efficiently.
    year_start = {
        2022: np.datetime64('2022-01-01'),
        2023: np.datetime64('2023-01-01'),
        2024: np.datetime64('2024-01-01'),
    }
    year_days = {2022: 365, 2023: 365, 2024: 366}

    for chunk_start in range(0, num_rows, chunk_size):
        chunk_rows = min(chunk_size, num_rows - chunk_start)
        transaction_id = np.arange(1 + chunk_start, 1 + chunk_start + chunk_rows)

        year = rng.choice(years, size=chunk_rows, p=year_prob_arr)
        customer_id = rng.integers(1, num_customers + 1, size=chunk_rows)
        product_id = rng.integers(1, num_products + 1, size=chunk_rows)

        # Amount: right-skewed, clipped to tutorial-friendly range.
        amount = rng.lognormal(mean=4.2, sigma=0.8, size=chunk_rows)
        amount = np.clip(amount, 10, 1000).round(2)

        # Date consistent with selected year (fully vectorized; no per-row loop).
        day_offsets = np.empty(chunk_rows, dtype=int)
        transaction_date = np.empty(chunk_rows, dtype='datetime64[D]')

        for y in (2022, 2023, 2024):
            mask = year == y
            if mask.any():
                offsets = rng.integers(0, year_days[y], size=int(mask.sum()))
                day_offsets[mask] = offsets
                transaction_date[mask] = year_start[y] + offsets.astype('timedelta64[D]')

        payment_method = rng.choice(payment_methods, size=chunk_rows, p=payment_prob)

        df_transactions_chunk = pd.DataFrame(
            {
                'transaction_id': transaction_id,
                'year': year,
                'customer_id': customer_id,
                'amount': amount,
                'product_id': product_id,
                'transaction_date': pd.to_datetime(transaction_date),
                'payment_method': payment_method,
            }
        )

        df_transactions_chunk.to_csv(
            output_path,
            mode='w' if not wrote_header else 'a',
            header=not wrote_header,
            index=False,
        )
        wrote_header = True

    print(f"   ✓ Created with {num_rows:,} rows ({output_path.stat().st_size / 1024**2:.1f} MB on disk)")
    return output_path


def create_orders_dataset(
    folder: Path = data_path,
    csv_file: str = 'orders.csv',
    num_rows: int = 2_500_000,
    *,
    seed: int = 42,
    chunk_size: int = 250_000,
    num_products: int = 10_000,
    num_customers: int = 500_000,
    num_stores: int = 500,
    start_date: str = '2024-01-01',
    days: int = 366,
    seasonality: bool = True,
):
    """Create an orders table for the practical example.

    Keeps original columns (order_id, product_id, quantity, price, customer_id,
    order_date) but:
    - vectorizes date generation
    - writes in chunks
    - adds useful analysis columns (store_id, channel, status)
    """

    print(f"6. Creating {csv_file}...")

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    output_path = folder / csv_file

    # ------------------------------------------------------------------------
    # OLD VERSION (kept for the tutorial)
    # ------------------------------------------------------------------------
    # num_orders = 2_500_000
    # np.random.seed(42)
    # orders_data = {
    #     'order_id': range(1, num_orders + 1),
    #     'product_id': np.random.randint(1, 5000, num_orders),
    #     'quantity': np.random.randint(1, 10, num_orders),
    #     'price': np.random.uniform(10, 500, num_orders).round(2),
    #     'customer_id': np.random.randint(1, 100000, num_orders),
    #     'order_date': [datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))
    #                    for _ in range(num_orders)]
    # }
    # pd.DataFrame(orders_data).to_csv(output_path, index=False)

    # ------------------------------------------------------------------------
    # NEW VERSION
    # ------------------------------------------------------------------------
    if num_rows <= 0:
        raise ValueError("num_rows must be > 0")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if num_products <= 0 or num_customers <= 0 or num_stores <= 0:
        raise ValueError("num_products/num_customers/num_stores must be > 0")
    if days <= 0:
        raise ValueError("days must be > 0")

    rng = np.random.default_rng(seed)
    wrote_header = False

    product_ids = np.arange(1, num_products + 1)
    popularity = rng.pareto(a=1.35, size=num_products) + 1.0
    product_prob = popularity / popularity.sum()

    product_unit_price = rng.lognormal(mean=3.5, sigma=0.7, size=num_products)
    product_unit_price = np.clip(product_unit_price, 10, 500).round(2)

    channels = np.array(['online', 'store', 'marketplace'])
    channel_prob = np.array([0.55, 0.35, 0.10])

    statuses = np.array(['paid', 'shipped', 'delivered', 'returned', 'cancelled'])
    status_prob = np.array([0.18, 0.20, 0.55, 0.04, 0.03])

    start_date_np = np.datetime64(start_date)
    day_index = np.arange(days)
    calendar = start_date_np + day_index.astype('timedelta64[D]')

    if seasonality:
        weekday = ((calendar.astype('datetime64[D]').astype('int64') + 4) % 7).astype(int)
        weekday_weights = np.array([0.95, 0.95, 1.00, 1.02, 1.08, 1.15, 1.12])
        weights = weekday_weights[weekday]
        date_prob = (weights / weights.sum()).astype(float)
    else:
        date_prob = None

    for chunk_start in range(0, num_rows, chunk_size):
        chunk_rows = min(chunk_size, num_rows - chunk_start)
        order_id = np.arange(1 + chunk_start, 1 + chunk_start + chunk_rows)

        product_id = rng.choice(product_ids, size=chunk_rows, p=product_prob)
        quantity = rng.integers(1, 10, size=chunk_rows)
        unit_price = product_unit_price[product_id - 1]
        price = (unit_price * quantity).round(2)

        customer_id = rng.integers(1, num_customers + 1, size=chunk_rows)
        store_id = rng.integers(1, num_stores + 1, size=chunk_rows)
        channel = rng.choice(channels, size=chunk_rows, p=channel_prob)
        status = rng.choice(statuses, size=chunk_rows, p=status_prob)

        if date_prob is None:
            day_offsets = rng.integers(0, days, size=chunk_rows)
        else:
            day_offsets = rng.choice(day_index, size=chunk_rows, replace=True, p=date_prob)
        order_date = start_date_np + day_offsets.astype('timedelta64[D]')

        df_orders_chunk = pd.DataFrame(
            {
                'order_id': order_id,
                'product_id': product_id,
                'quantity': quantity,
                'price': price,
                'customer_id': customer_id,
                'order_date': pd.to_datetime(order_date),
                'store_id': store_id,
                'channel': channel,
                'status': status,
            }
        )

        df_orders_chunk.to_csv(
            output_path,
            mode='w' if not wrote_header else 'a',
            header=not wrote_header,
            index=False,
        )
        wrote_header = True

    print(f"   ✓ Created with {num_rows:,} rows ({output_path.stat().st_size / 1024**2:.1f} MB on disk)")
    return output_path


def main(
    folder: Path = data_path,
    *,
    create_gzip_copies: bool = True,
    gzip_min_size_mb: float = 25.0,
    remove_original_csv: bool = False,
):
    """Generate all datasets used in the large-datasets tutorial.

    Parameters
    ----------
    folder : pathlib.Path
        Where to write the generated files.
    create_gzip_copies : bool, optional
        If True, create `.csv.gz` copies for large CSVs to make it easier to
        commit them to GitHub.
    gzip_min_size_mb : float, optional
        Only compress CSVs larger than this threshold.
    remove_original_csv : bool, optional
        If True, delete the original `.csv` after creating the `.csv.gz` copy.
        Defaults to False to avoid breaking notebooks that expect `.csv`.
    """

    print("Starting data generation...\n")

    # ---------------------------------------------------------------------
    # Join-consistent defaults
    # ---------------------------------------------------------------------
    # To make joins predictable in the tutorial, we keep a shared set of ID
    # domains. That way:
    # - fact tables (sales/orders/transactions/ratings) all reference IDs that
    #   exist in the corresponding dimension tables (customers/products)
    # - learners can join without needing extra filtering or "missing key" fixes
    #
    # You can scale these up/down depending on your machine.
    NUM_CUSTOMERS = 500_000
    NUM_PRODUCTS = 10_000
    NUM_STORES = 500

    created_paths = [
        create_sales_dataset(folder=folder, num_customers=NUM_CUSTOMERS, num_products=NUM_PRODUCTS, num_stores=NUM_STORES),
        create_customers_dataset(folder=folder, num_rows=NUM_CUSTOMERS),
        create_ratings_dataset(folder=folder, num_users=NUM_CUSTOMERS, num_products=NUM_PRODUCTS),
        create_products_dataset(folder=folder, num_rows=NUM_PRODUCTS),
        create_transactions_dataset(folder=folder, num_customers=NUM_CUSTOMERS, num_products=NUM_PRODUCTS),
        create_orders_dataset(folder=folder, num_customers=NUM_CUSTOMERS, num_products=NUM_PRODUCTS, num_stores=NUM_STORES),
    ]

    if create_gzip_copies:
        print("\nCreating compressed copies (.csv.gz) for GitHub...")
        for path in created_paths:
            if not path.exists():
                continue
            if path.suffix.lower() != '.csv':
                continue

            size_mb = path.stat().st_size / 1024**2
            if size_mb < gzip_min_size_mb:
                continue

            gz_path = _gzip_csv_copy(path, remove_original=remove_original_csv)
            gz_size_mb = gz_path.stat().st_size / 1024**2
            print(f"   ✓ {gz_path.name:<30} {gz_size_mb:>8.1f} MB")

    print("\n" + "=" * 60)
    print("DATA GENERATION COMPLETE!")
    print("=" * 60)

    total_size = 0.0
    for path in created_paths:
        if path.exists():
            size_mb = path.stat().st_size / 1024**2
            total_size += size_mb
            print(f"✓ {path.name:<30} {size_mb:>8.1f} MB")

    print("=" * 60)
    print(f"Total size: {total_size:.1f} MB")


if __name__ == "__main__":
    main()
