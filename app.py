import streamlit as st
import pandas as pd
from db_functions import (
    connect_to_db,
    get_basic_info,
    get_additional_tables,
    get_categories,
    get_suppliers,
    add_new_product_manual_id,
    get_all_products,
    get_product_history,
    place_reorder,
    get_pending_reorders,
    mark_reorder_as_received
)

# Sidebar with navigation option
st.sidebar.title("📊 Inventory Management Dashboard")
option = st.sidebar.radio("Select Option", ["Basic Information", "Operational Tasks"])

# Main app title
st.title("📦 Inventory & Supply Chain Dashboard")

# Connect to DB
db = connect_to_db()
cursor = db.cursor(dictionary=True)

# ------------------------- BASIC INFORMATION PAGE --------------------------
if option == "Basic Information":
    st.header("📌 Basic Metrics")

    # Fetch summary metrics from DB
    basic_info = get_basic_info(cursor)

    # Prepare layout: 2 rows, 3 columns for 6 metrics
    cols = st.columns(3)
    keys = list(basic_info.keys())

    for i in range(3):
        cols[i].metric(label=keys[i], value=basic_info[keys[i]])

    cols = st.columns(3)
    for i in range(3, 6):
        cols[i - 3].metric(label=keys[i], value=basic_info[keys[i]])

    st.success("Summary data reflects the latest records.")
    st.markdown("---")

    # Fetch and display detailed tables
    tables = get_additional_tables(cursor)
    for label, data in tables.items():
        st.subheader(label)
        df = pd.DataFrame(data)
        st.dataframe(df)
        st.divider()

# ------------------------- OPERATIONAL TASKS PAGE --------------------------
elif option == "Operational Tasks":
    st.header("🛠️ Operational Tasks")

    # Select the task from dropdown
    selected_task = st.selectbox("Choose a task", ["Add New Product", "Product History", "Place Reorder","Receive Orders"])

    # ------------------ Add New Product ------------------
    if selected_task == "Add New Product":
        st.subheader("➕ Enter New Product")

        # Fetch categories and suppliers
        categories = get_categories(cursor)
        suppliers = get_suppliers(cursor)

        with st.form("add_product_form"):
            product_name = st.text_input("Product Name")
            product_category = st.selectbox("Category", categories)
            product_price = st.number_input("Price", min_value=0.0, format="%.2f")
            product_stock = st.number_input("Stock Quantity", min_value=0, step=1)
            reorder_level = st.number_input("Reorder Level", min_value=0, step=1)
            supplier_ids = [s['supplier_id'] for s in suppliers]
            supplier_names = [s['supplier_name'] for s in suppliers]

            supplier_id = st.selectbox(
                "Supplier",
                options=supplier_ids,
                format_func=lambda x: supplier_names[supplier_ids.index(x)]
            )

            submitted = st.form_submit_button("Add Product")

            if submitted:
                if not product_name:
                    st.error("Please enter the product name.")
                else:
                    try:
                        add_new_product_manual_id(
                            cursor,
                            db,
                            product_name,
                            product_category,
                            product_price,
                            product_stock,
                            reorder_level,
                            supplier_id,
                        )
                        st.success(f"✅ Product '{product_name}' added successfully!")
                    except Exception as e:
                        st.error(f"❌ Error adding product: {e}")

    # ------------------ Placeholder for future tasks ------------------
    elif selected_task == "Product History":
        st.subheader("📖 Product Inventory History")

        # Get products list
        products = get_all_products(cursor)
        product_names = [p['product_name'] for p in products]
        product_ids = [p['product_id'] for p in products]

        selected_product_name = st.selectbox("Select a product", options=product_names)

        if selected_product_name:
            selected_product_id = product_ids[product_names.index(selected_product_name)]
            history_data = get_product_history(cursor, selected_product_id)

            if history_data:
                df = pd.DataFrame(history_data)
                st.dataframe(df)
            else:
                st.info("No history records found for this product.")

    elif selected_task == "Place Reorder":
        st.subheader("📦 Place a Reorder")

        # Fetch all products for dropdown
        products = get_all_products(cursor)
        product_names = [p['product_name'] for p in products]
        product_ids = [p['product_id'] for p in products]

        selected_product_name = st.selectbox("Select Product", options=product_names)
        reorder_qty = st.number_input("Reorder Quantity", min_value=1, step=1)

        if st.button("Place Reorder"):
            if not selected_product_name:
                st.error("Please select a product.")
            elif reorder_qty <= 0:
                st.error("Reorder quantity must be greater than zero.")
            else:
                selected_product_id = product_ids[product_names.index(selected_product_name)]
                try:
                    place_reorder(cursor, db, selected_product_id, reorder_qty)
                    st.success(f"✅ Reorder placed for '{selected_product_name}' with quantity {reorder_qty}.")
                except Exception as e:
                    st.error(f"❌ Error placing reorder: {e}")

    elif selected_task == "Receive Orders ":
        st.subheader("📥 Mark Reorder as Received")

        # Fetch pending reorders
        pending_reorders = get_pending_reorders(cursor)
        if not pending_reorders:
            st.info("✅ No pending reorders to receive.")
        else:
            reorder_ids = [r['reorder_id'] for r in pending_reorders]
            reorder_labels = [f"ID {r['reorder_id']} - {r['product_name']}" for r in pending_reorders]

            selected_label = st.selectbox("Select Reorder to Mark as Received", options=reorder_labels)

            if selected_label:
                selected_reorder_id = reorder_ids[reorder_labels.index(selected_label)]

                if st.button("Mark as Received"):
                    try:
                        mark_reorder_as_received(cursor, db, selected_reorder_id)
                        st.success(f"✅ Reorder ID {selected_reorder_id} marked as received.")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

# Close DB connection
cursor.close()
db.close()
