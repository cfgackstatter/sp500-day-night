"""Main entry point for Dash S&P 500 Day vs Night Returns web app.

This file is named 'application.py' for AWS Elastic Beanstalk compatibility.
The Dash app object is exposed as 'application' for EB's WSGI server.
"""

from dash import Dash
from layout import create_layout
from data_utils import load_all_data

# Initialize Dash app with meta tags for responsive design
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)

app.title = "Day vs Night Returns"

# Load all data at startup (shared across all callbacks)
print("Loading historical data for all symbols...")
data_cache = load_all_data()
print("Data loading complete!")

# Create layout and pass data cache
app.layout = create_layout(app, data_cache)

# Expose server for AWS Elastic Beanstalk
application = app.server

if __name__ == "__main__":
    # For local development
    app.run(host="0.0.0.0", port=8080, debug=True)
