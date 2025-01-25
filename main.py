import streamlit as st
import pandas as pd

# Set page configuration
st.set_page_config(page_title="Real Or Fake", layout="wide")

# Add a title to the page
st.markdown(f"<h1 class='rtl'>Real Or Fake</h1>", unsafe_allow_html=True)

# Load the data
df = pd.read_csv('final_labeled_data.csv')

# Rename columns for user-friendly display
df.rename(columns={
    'job_id': 'Job ID',
    'title': 'Title',
    'company_name': 'Company Name',
    'location': 'Location',
    'salary': 'Salary',
    'job_type': 'Job Type',
    'job_url': 'Job URL',
    'prediction': 'Real Or Fake'
}, inplace=True)


# Replace numeric values in 'Real Or Fake' column with descriptive labels
df['Real Or Fake'] = df['Real Or Fake'].apply(lambda x: 'Real' if int(x) == 0 else 'Fake')

# Rearrange columns
df = df[['Job ID', 'Title', 'Company Name', 'Location', 'Salary', 'Job Type', 'Job URL', 'Real Or Fake']]

# Create filters in a single row using st.columns
st.markdown("### Filter Rows by Column Values")

columns = st.columns(len(df.columns) - 3)  # Exclude 'Job URL' and 'Confidence'
filters = {}

for col, column_name in zip(columns, df.columns):
    if column_name not in ['Job URL', 'Confidence']:
        with col:
            filters[column_name] = st.text_input(f"{column_name}", key=column_name)

# Apply filters
filtered_df = df.copy()
filters_filled = False  # Track if any filter has input

for column, user_input in filters.items():
    if user_input:  # Only filter if input is not empty
        filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(user_input, case=False, na=False)]
        filters_filled = True  # At least one filter is filled

# If no filters are filled, show only the first 20 rows
if not filters_filled:
    filtered_df = filtered_df.head(20)

# Replace NaN in the Salary column with "Not Available"
filtered_df['Salary'] = filtered_df['Salary'].fillna('Not Available')

# Replace 'Job URL' column with clickable "Apply here"
filtered_df['Job URL'] = filtered_df['Job URL'].apply(
    lambda x: f'<a href="{x}" target="_blank">Apply here</a>' if pd.notna(x) else ''
)

# Create clickable 'Job ID' links
filtered_df['Job ID'] = filtered_df['Job ID'].apply(
    lambda job_id: f"<a href='/job_detailed?job_id={job_id}'>{job_id}</a>"  # Link to job details page by Job ID
)

# CSS for scrollable table with left-to-right text alignment
table_style = """
    <style>
        .scrollable-table {
            max-height: 400px; 
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            direction: ltr; /* Left-to-right text direction */
        }
        .scrollable-table table {
            width: 100%;
            text-align: left; /* Align text to the left */
        }
        .scrollable-table th {
            text-align: left; /* Align table header text to the left */
            background-color: #f2f2f2;
            padding: 10px;
        }
        .scrollable-table td {
            padding: 10px;
        }
    </style>
"""

# Display the table within a scrollable box
st.markdown(table_style, unsafe_allow_html=True)
st.markdown(f'<div class="scrollable-table">{filtered_df.to_html(escape=False, index=False)}</div>', unsafe_allow_html=True)
