import os

import pandas as pd
import plotly.express as px
import streamlit as st


CLEANED_FILE = 'Cleaned_Retail_Sales_Data.xlsx'
RAW_FILE = 'Retail_Sales_Intern_Dataset.xlsx'

# Label used in the filters for records with a missing brand or outlet
MISSING_LABEL = '(Missing)'

st.set_page_config(page_title='Retail Sales Dashboard', page_icon='📊', layout='wide')


@st.cache_data
def load_cleaned_data(file_path):
    """Load the cleaned dataset created by the notebook."""

    df = pd.read_excel(file_path)

    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Month'] = df['Date'].dt.strftime('%Y-%m')

    # Show missing brands/outlets as a filter option instead of hiding them
    df['Brand'] = df['Brand'].fillna(MISSING_LABEL)
    df['Outlet'] = df['Outlet'].fillna(MISSING_LABEL)

    df['Data_Quality_Note'] = df['Data_Quality_Note'].fillna('')

    return df


@st.cache_data
def count_raw_records(file_path):
    """Count the records in the raw dataset (used for the excluded count)."""

    if not os.path.exists(file_path):
        return None

    return len(pd.read_excel(file_path, sheet_name='Raw_Sales_Data'))


def create_sales_summary(df, group_column):
    """Total net sales, units and invoices for each group."""

    summary = df.groupby(group_column).agg(
        Total_Net_Sales=('Net_Sales_LKR', 'sum'),
        Total_Units_Sold=('Quantity', 'sum'),
        Number_of_Invoices=('Invoice_No', 'nunique')
    ).reset_index()

    summary['Average_Transaction_Value'] = (
        summary['Total_Net_Sales'] / summary['Number_of_Invoices']
    )

    return summary.sort_values(by='Total_Net_Sales', ascending=False)


def format_lkr(value):
    return f'LKR {value:,.2f}'


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
if not os.path.exists(CLEANED_FILE):
    st.error(f'{CLEANED_FILE} not found. Run Retail_Sales_Analysis.ipynb first and '
             f'place the file in the same folder as app.py.')
    st.stop()

cleaned_df = load_cleaned_data(CLEANED_FILE)

raw_record_count = count_raw_records(RAW_FILE)

# Sidebar filters

st.sidebar.header('Filters')

min_date = cleaned_df['Date'].min().date()
max_date = cleaned_df['Date'].max().date()

selected_dates = st.sidebar.date_input(
    'Date range',
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

include_missing_date = st.sidebar.checkbox(
    'Include records with a missing date',
    value=True
)

brand_options = sorted(cleaned_df['Brand'].unique())

selected_brands = st.sidebar.multiselect(
    'Brand',
    options=brand_options,
    default=brand_options
)

outlet_options = sorted(cleaned_df['Outlet'].unique())

selected_outlets = st.sidebar.multiselect(
    'Outlet',
    options=outlet_options,
    default=outlet_options
)

# The date input returns one date while the user is still choosing the range
if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date, end_date = min_date, max_date

in_date_range = cleaned_df['Date'].dt.date.between(start_date, end_date)

if include_missing_date:
    in_date_range = in_date_range | cleaned_df['Date'].isna()

filtered_df = cleaned_df[
    in_date_range &
    cleaned_df['Brand'].isin(selected_brands) &
    cleaned_df['Outlet'].isin(selected_outlets)
]

st.sidebar.caption(f'{len(filtered_df)} of {len(cleaned_df)} records selected')

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title('Retail Sales Dashboard')
st.caption('Infinite Business Ventures (Pvt) Ltd – cleaned retail sales data, July–September 2026')

if filtered_df.empty:
    st.warning('No records match the selected filters.')
    st.stop()

sales_tab, quality_tab = st.tabs(['Sales Performance', 'Data Quality'])


# Tab 1 – Sales performance

with sales_tab:

    total_net_sales = filtered_df['Net_Sales_LKR'].sum()
    total_units_sold = filtered_df['Quantity'].sum()
    total_invoices = filtered_df['Invoice_No'].nunique()
    average_transaction_value = total_net_sales / total_invoices

    kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

    kpi_1.metric('Total Net Sales', format_lkr(total_net_sales))
    kpi_2.metric('Units Sold', f'{total_units_sold:,.0f}')
    kpi_3.metric('Invoices', f'{total_invoices:,}')
    kpi_4.metric('Average Transaction Value', format_lkr(average_transaction_value))

    st.caption('Invoices = unique Invoice_No (one invoice = one sales line). '
               'ATV = Total Net Sales ÷ Invoices.')

    # Monthly trend
    monthly_summary = create_sales_summary(
        filtered_df.dropna(subset=['Month']), 'Month'
    ).sort_values(by='Month')

    monthly_chart = px.line(
        monthly_summary,
        x='Month',
        y='Total_Net_Sales',
        markers=True,
        title='Monthly Net Sales Trend',
        labels={'Total_Net_Sales': 'Total Net Sales (LKR)', 'Month': 'Month'}
    )
    monthly_chart.update_yaxes(tickformat=',.0f', rangemode='tozero')
    monthly_chart.update_xaxes(type='category')

    st.plotly_chart(monthly_chart, width='stretch')

    # Brand and outlet charts side by side
    brand_column, outlet_column = st.columns(2)

    brand_summary = create_sales_summary(filtered_df, 'Brand')

    brand_chart = px.bar(
        brand_summary.sort_values(by='Total_Net_Sales'),
        x='Total_Net_Sales',
        y='Brand',
        orientation='h',
        title='Brand-wise Net Sales',
        labels={'Total_Net_Sales': 'Total Net Sales (LKR)', 'Brand': 'Brand'}
    )
    brand_chart.update_xaxes(tickformat=',.0f')

    brand_column.plotly_chart(brand_chart, width='stretch')

    outlet_summary = create_sales_summary(filtered_df, 'Outlet')

    outlet_chart = px.bar(
        outlet_summary.sort_values(by='Total_Net_Sales'),
        x='Total_Net_Sales',
        y='Outlet',
        orientation='h',
        title='Outlet-wise Net Sales',
        labels={'Total_Net_Sales': 'Total Net Sales (LKR)', 'Outlet': 'Outlet'}
    )
    outlet_chart.update_xaxes(tickformat=',.0f')

    outlet_column.plotly_chart(outlet_chart, width='stretch')

    # Top products and brand table
    product_column, table_column = st.columns(2)

    product_column.subheader('Top 5 Products by Net Sales')
    product_column.dataframe(
        create_sales_summary(filtered_df, 'Product').head(5),
        hide_index=True,
        column_config={
            'Total_Net_Sales': st.column_config.NumberColumn('Net Sales (LKR)', format='%,.2f'),
            'Total_Units_Sold': st.column_config.NumberColumn('Units', format='%d'),
            'Number_of_Invoices': st.column_config.NumberColumn('Invoices'),
            'Average_Transaction_Value': st.column_config.NumberColumn('ATV (LKR)', format='%,.2f')
        }
    )

    table_column.subheader('Brand Summary')
    table_column.dataframe(
        brand_summary,
        hide_index=True,
        column_config={
            'Total_Net_Sales': st.column_config.NumberColumn('Net Sales (LKR)', format='%,.2f'),
            'Total_Units_Sold': st.column_config.NumberColumn('Units', format='%d'),
            'Number_of_Invoices': st.column_config.NumberColumn('Invoices'),
            'Average_Transaction_Value': st.column_config.NumberColumn('ATV (LKR)', format='%,.2f')
        }
    )

# Tab 2 – Data quality summary

with quality_tab:

    notes = cleaned_df['Data_Quality_Note']

    records_corrected = notes.str.contains('recovered|calculated|standardised').sum()
    records_flagged = notes.str.contains('kept as missing|set to missing').sum()
    remaining_discrepancies = cleaned_df['Sales_Discrepancy'].sum()

    if raw_record_count is not None:
        records_excluded = raw_record_count - len(cleaned_df)
    else:
        records_excluded = None

    st.caption('This tab always shows the full dataset (filters are not applied).')

    quality_1, quality_2, quality_3, quality_4 = st.columns(4)

    quality_1.metric('Records corrected', int(records_corrected),
                     help='Numeric value recovered from the net sales formula, or brand text standardised')
    quality_2.metric('Records excluded',
                     'N/A' if records_excluded is None else int(records_excluded),
                     help='Exact duplicate rows removed')
    quality_3.metric('Records flagged', int(records_flagged),
                     help='Date, brand or outlet missing or unknown – record kept')
    quality_4.metric('Discrepancies remaining', int(remaining_discrepancies),
                     help='Net sales not matching Quantity × Unit Price × (1 − Discount) within LKR 0.01')

    if raw_record_count is None:
        st.info(f'Place {RAW_FILE} next to app.py to show the excluded record count.')

    st.subheader('Data Quality Log')

    log_columns = [
        'Invoice_No', 'Data_Quality_Note',
        'Original_Brand', 'Brand', 'Original_Outlet', 'Outlet',
        'Original_Quantity', 'Quantity',
        'Original_Unit_Price_LKR', 'Unit_Price_LKR',
        'Original_Discount_Rate', 'Discount_Rate',
        'Original_Net_Sales_LKR', 'Net_Sales_LKR'
    ]

    st.dataframe(
        cleaned_df.loc[notes != '', log_columns],
        hide_index=True,
        width='stretch'
    )
