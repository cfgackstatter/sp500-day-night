"""Main entry point for Dash Day vs Night Returns app.

Named application.py for AWS Elastic Beanstalk; WSGI target is `application`.
"""

from dash import Dash

from data_utils import load_all_data, load_names, load_tickers
from layout import create_layout

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1.0"}],
)
app.title = "Day vs Night Returns"

print("Loading historical data...")
data_cache = load_all_data(load_tickers())
name_cache = load_names(list(data_cache))
print("Data loading complete!")

app.layout = create_layout(app, data_cache, name_cache)
application = app.server

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
