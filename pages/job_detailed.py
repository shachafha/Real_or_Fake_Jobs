import streamlit as st
import pandas as pd

# Load the data
df = pd.read_csv('./final_labeled_data.csv')

# Replace NaN in the salary column with "Not Available"
df['salary'] = df['salary'].fillna('Not Available')

# Define helper function for query params
def get_query_param(param):
    query_string = st.query_params
    return query_string.get(param, None)

# Get job_id from query parameters
job_id = get_query_param("job_id")

# If a job_id is selected, display the job details
if job_id:
    # Find the job details for the selected job_id
    job_details = df[df['job_id'] == int(job_id)].iloc[0]

    # Job title and confidence
    st.markdown(f"<h3 style='text-align: center;'>Job Details for {job_details['title']} at {job_details['company_name']}</h3>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center;'>We are {float(job_details['probability']) * 100:.1f}% sure that this job is</h4>", unsafe_allow_html=True)

    # Display prediction with colored badge and image
    col1, col2, col3 = st.columns([4, 6, 1])
    if int(job_details['prediction']) == 0:
        badge = "<span style='color: green; font-size: 16px;'></span>"
        image = './images/real.jpg'
    else:
        badge = "<span style='color: red; font-size: 16px;'></span>"
        image = './images/fake.jpg'

    with col2:
        st.image(image, width=150)
        st.markdown(badge, unsafe_allow_html=True)

    # Display job details in a card-like format
    st.markdown(f"""
        <div style="padding: 15px; border: 1px solid #ccc; border-radius: 10px; background-color: #f9f9f9; margin-bottom: 20px;">
            <p><strong>Company Name:</strong> {job_details['company_name']}</p>
            <p><strong>Location:</strong> {job_details.get('location', 'Not Specified')}</p>
            <p><strong>Salary:</strong> {job_details['salary']}</p>
            <p><strong>Job Type:</strong> {job_details['job_type']}</p>
            <a href='{job_details['job_url']}' target='_blank' style='color: #007BFF;'>Apply here</a>
        </div>
    """, unsafe_allow_html=True)
    # Warning for fake jobs
    if job_details['prediction'] == 0:
        st.markdown(f"<p style='color: red; font-size: 14px;'><strong>🚫 Apply at your own risk! 🚫</strong></p>", unsafe_allow_html=True)

    # Scrollable Job Description with enhanced styling
    job_description = job_details.get('job_description', 'No description available.')
    if 'Profile insights' in job_description:
        job_description = job_description[job_description.find('Full job description')+20:]

    scroll_box_style = """
        <style>
            .scroll-box {
                border: 1px solid #4CAF50; 
                padding: 10px; 
                height: 200px; 
                overflow-y: scroll; 
                background-color: #f0f8ff; 
                border-radius: 5px;
            }
        </style>
    """
    # title job description
    st.markdown(f"### Job Description")
    st.markdown(scroll_box_style, unsafe_allow_html=True)
    st.markdown(f"<div class='scroll-box'>{job_description}</div>", unsafe_allow_html=True)


else:
    st.write("No job selected.")
