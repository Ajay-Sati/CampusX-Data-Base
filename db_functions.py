import mysql.connector

def connect_to_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="CampusX@21",
        database="dummy_project"
    )

def get_basic_info(cursor):
    queries = {
        "Total Suppliers": "SELECT COUNT(*) AS count FROM suppliers",
        "Total Products": "SELECT COUNT(*) AS count FROM products",
        "Total Categories Dealing": "SELECT COUNT(DISTINCT category) AS count FROM products",
        "Total Sale Value (Last 3 Months)": """
            SELECT ROUND(SUM(ABS(se.change_quantity) * p.price), 2) AS total_sale
            FROM stock_entries se
            JOIN products p ON se.product_id = p.product_id
            WHERE se.change_type = 'Sale'
              AND se.entry_date >= (
                  SELECT DATE_SUB(MAX(entry_date), INTERVAL 3 MONTH) FROM stock_entries)
        """,
        "Total Restock Value (Last 3 Months)": """
            SELECT ROUND(SUM(se.change_quantity * p.price), 2) AS total_restock
            FROM stock_entries se
            JOIN products p ON se.product_id = p.product_id
            WHERE se.change_type = 'Restock'
              AND se.entry_date >= (
                  SELECT DATE_SUB(MAX(entry_date), INTERVAL 3 MONTH) FROM stock_entries)
        """,
        "Below Reorder & No Pending Reorders": """
            SELECT COUNT(*) AS below_reorder
            FROM products p
            WHERE p.stock_quantity < p.reorder_level
              AND p.product_id NOT IN (
                  SELECT DISTINCT product_id FROM reorders WHERE status = 'Pending')
        """
    }
    results = {}
    for label, query in queries.items():
        cursor.execute(query)
        row = cursor.fetchone()
        results[label] = list(row.values())[0] if row else 0
    return results

def get_additional_tables(cursor):
    queries = {
        "Suppliers Contact Details": "SELECT supplier_name, contact_name, email, phone FROM suppliers",
        "Products with Supplier and Stock": """
            SELECT 
                p.product_name,
                s.supplier_name,
                p.stock_quantity,
                p.reorder_level
            FROM products p
            JOIN suppliers s ON p.supplier_id = s.supplier_id
            ORDER BY p.product_name ASC
        """,
        "Products Needing Reorder": """
            SELECT product_name, stock_quantity, reorder_level
            FROM products
            WHERE stock_quantity <= reorder_level
        """
    }
    tables = {}
    for label, query in queries.items():
        cursor.execute(query)
        tables[label] = cursor.fetchall()
    return tables

def get_categories(cursor):
    """Fetch distinct product categories for dropdown"""
    cursor.execute("SELECT DISTINCT category FROM products ORDER BY category ASC")
    rows = cursor.fetchall()
    return [row['category'] for row in rows]

def get_suppliers(cursor):
    """Fetch all suppliers with their IDs and names for dropdown"""
    cursor.execute("SELECT supplier_id, supplier_name FROM suppliers ORDER BY supplier_name ASC")
    return cursor.fetchall()

def add_new_product_manual_id(cursor, db, p_name, p_category, p_price, p_stock, p_reorder, p_supplier):
    """
    Calls the stored procedure AddNewProductManualID to add a new product
    along with initial shipment and stock entries.
    """
    proc_call = "CALL AddNewProductManualID(%s, %s, %s, %s, %s, %s)"
    params = (p_name, p_category, p_price, p_stock, p_reorder, p_supplier)
    cursor.execute(proc_call, params)
    db.commit()



def get_all_products(cursor):
    """Fetch product ID and name for dropdown selection"""
    cursor.execute("SELECT product_id, product_name FROM products ORDER BY product_name")
    return cursor.fetchall()

def get_product_history(cursor, product_id):
    """Query the existing view without modifying it"""
    query = """
        SELECT * FROM product_inventory_history
        WHERE product_id = %s
        ORDER BY record_date DESC
    """
    cursor.execute(query, (product_id,))
    return cursor.fetchall()


def place_reorder(cursor, db, product_id, reorder_quantity):
    """
    Inserts a new reorder record for the given product and quantity.
    reorder_id is automatically incremented by 1 based on max reorder_id in the table.
    reorder_date is current date, status is 'Ordered'.
    """
    query = """
    INSERT INTO reorders (reorder_id, product_id, reorder_quantity, reorder_date, status)
    SELECT 
        IFNULL(MAX(reorder_id), 0) + 1,
        %s,
        %s,
        CURDATE(),
        'Ordered'
    FROM reorders;
    """
    cursor.execute(query, (product_id, reorder_quantity))
    db.commit()



def get_pending_reorders(cursor):
    """Fetch reorder IDs and product names for dropdown where status is 'Ordered'"""
    cursor.execute("""
        SELECT r.reorder_id, p.product_name
        FROM reorders r
        JOIN products p ON r.product_id = p.product_id
        WHERE r.status = 'Ordered'
        ORDER BY r.reorder_id
    """)
    return cursor.fetchall()

def mark_reorder_as_received(cursor, db, reorder_id):
    """Call the stored procedure to mark reorder as received"""
    cursor.callproc('MarkReorderAsReceived', [reorder_id])
    db.commit()